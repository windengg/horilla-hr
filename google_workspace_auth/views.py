"""
google_workspace_auth/views.py

"Sign in with Google", restricted to one Google Workspace domain.

Flow:
  1. google_login builds a Google OAuth authorization URL and redirects there.
  2. The user authenticates with Google (their Workspace account). If that
     account has been suspended or deleted in Workspace, Google itself
     refuses to complete this step -- that is what blocks a de-provisioned
     user's next login, not anything checked here.
  3. google_callback exchanges the returned code for tokens, then verifies
     the ID token's signature and claims *server-side*. The `hd` (hosted
     domain) claim is what proves the account belongs to the configured
     Workspace domain -- the `hd` param sent in step 1 is only a UX hint
     and is never trusted on its own.
  4. On success, an existing Horilla user is logged in by email match, or
     (if enabled) a new user + employee record is created on first login.
"""

import logging
import os

# Google's token response commonly reports the granted scopes back in a
# different form than what was requested (reordered, or shorthand like
# "email"/"profile" instead of the full googleapis.com URL) -- oauthlib
# treats any such mismatch as a hard error by default and Flow.fetch_token()
# raises it, which otherwise surfaces to the user as a generic "Google
# sign-in failed" even though the sign-in itself succeeded. This has to be
# set before Flow.fetch_token() runs, so it's set at import time here rather
# than only in settings/env.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.core.cache import cache
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from google_auth_oauthlib.flow import Flow

from employee.models import Employee
from google_workspace_auth.models import GoogleWorkspaceSettings

logger = logging.getLogger(__name__)

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# OAuth state tokens are short-lived and single-use; a stale entry left in
# cache past this window is not a login flow anyone is still completing.
STATE_TTL_SECONDS = 600


def _get_active_settings():
    return GoogleWorkspaceSettings.objects.filter(is_enabled=True).first()


def _build_flow(api, state=None, code_verifier=None):
    client_config = {
        "web": {
            "client_id": api.client_id,
            "client_secret": api.client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        state=state,
        redirect_uri=api.redirect_uri,
        # Google requires PKCE for this client type. login() and callback()
        # build separate Flow instances (state travels via Google's redirect,
        # so there's nothing else to reuse the same object across requests),
        # so the verifier generated at login time has to be handed back in
        # explicitly here at callback time -- see google_login/google_callback.
        autogenerate_code_verifier=(code_verifier is None),
        code_verifier=code_verifier,
    )


def google_login(request):
    """
    Redirect to Google's consent screen.
    """
    api = _get_active_settings()
    if not api:
        messages.error(request, _("Google sign-in is not configured."))
        return redirect("login")

    flow = _build_flow(api)
    authorization_url, state = flow.authorization_url(
        access_type="online",
        include_granted_scopes="true",
        # UX hint only -- Google does not enforce this, so the callback
        # verifies the domain again from the signed ID token's `hd` claim.
        hd=api.allowed_domain,
        prompt="select_account",
    )
    # The state travels via Google's redirect (a public round trip), so it is
    # verified against a copy the server itself holds, not just echoed back.
    cache.set(f"google_oauth_state_{state}", True, timeout=STATE_TTL_SECONDS)
    request.session["google_oauth_state"] = state
    # PKCE: the verifier generated for this authorization request must be
    # replayed on the token exchange in google_callback, which builds its
    # own Flow object -- so it's carried across the same way `state` is.
    request.session["google_oauth_code_verifier"] = flow.code_verifier
    return redirect(authorization_url)


def google_callback(request):
    """
    Handle Google's redirect back: exchange the code, verify the ID token,
    and log the matching (or newly provisioned) Horilla user in.
    """
    api = _get_active_settings()
    if not api:
        messages.error(request, _("Google sign-in is not configured."))
        return redirect("login")

    returned_state = request.GET.get("state")
    session_state = request.session.pop("google_oauth_state", None)
    code_verifier = request.session.pop("google_oauth_code_verifier", None)
    cached = cache.get(f"google_oauth_state_{returned_state}") if returned_state else None
    if not returned_state or returned_state != session_state or not cached:
        messages.error(
            request, _("Google sign-in session expired or is invalid. Please try again.")
        )
        return redirect("login")
    cache.delete(f"google_oauth_state_{returned_state}")

    if request.GET.get("error"):
        # e.g. the user clicked "Cancel" on Google's consent screen.
        messages.info(request, _("Google sign-in was cancelled."))
        return redirect("login")

    flow = _build_flow(api, state=returned_state, code_verifier=code_verifier)
    authorization_response = request.build_absolute_uri().replace("http://", "https://")
    try:
        flow.fetch_token(authorization_response=authorization_response)
    except Exception:
        logger.exception("Google OAuth token exchange failed")
        messages.error(request, _("Google sign-in failed. Please try again."))
        return redirect("login")

    credentials = flow.credentials
    try:
        id_info = google_id_token.verify_oauth2_token(
            credentials.id_token, google_requests.Request(), api.client_id
        )
    except Exception:
        logger.exception("Google ID token verification failed")
        messages.error(request, _("Could not verify your Google account."))
        return redirect("login")

    email = id_info.get("email")
    email_verified = id_info.get("email_verified")
    hosted_domain = id_info.get("hd")

    if not email or not email_verified:
        messages.error(request, _("Your Google account's email is not verified."))
        return redirect("login")

    if hosted_domain != api.allowed_domain:
        # Rejects personal @gmail.com accounts and other Workspace domains,
        # even if they somehow reached this point.
        logger.warning(
            "Google sign-in rejected for %s: hd=%r does not match configured domain %r",
            email,
            hosted_domain,
            api.allowed_domain,
        )
        messages.error(
            request,
            _("Only %(domain)s Google Workspace accounts may sign in.")
            % {"domain": api.allowed_domain},
        )
        return redirect("login")

    User = get_user_model()
    user = User.objects.filter(email__iexact=email).first()

    if user is None:
        if not api.auto_create_employee:
            messages.error(
                request, _("No Horilla account exists for %(email)s.") % {"email": email}
            )
            return redirect("login")
        user = _provision_user(User, email, id_info)
    else:
        employee = getattr(user, "employee_get", None)
        if employee is not None and not employee.is_active:
            messages.warning(
                request,
                _(
                    "This user is archived. Please contact the manager for more information."
                ),
            )
            return redirect("login")
        if not user.is_active:
            messages.warning(request, _("This account is inactive."))
            return redirect("login")

    # Constructed directly here rather than via authenticate(), so `.backend`
    # must be set explicitly -- login() requires it whenever more than one
    # AUTHENTICATION_BACKENDS is configured (always true here), otherwise it
    # raises ValueError. Same pattern used in onboarding/views.py.
    user.backend = "base.auth_backends.CompanyScopedBackend"
    login(request, user)
    messages.success(request, _("Signed in with Google."))
    return redirect("/")


def _provision_user(User, email, id_info):
    """
    Create a Horilla user + employee record for a first-time Google sign-in.
    The account is Google-only: it gets no usable password, so it cannot
    also be logged into with a guessed/leaked password later.
    """
    first_name = id_info.get("given_name", "") or ""
    last_name = id_info.get("family_name", "") or ""

    base_username = email.split("@")[0]
    username = base_username
    suffix = 1
    while User.objects.filter(username=username).exists():
        suffix += 1
        username = f"{base_username}{suffix}"

    user = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )
    user.set_unusable_password()
    user.save()

    Employee.objects.create(
        employee_user_id=user,
        employee_first_name=first_name or base_username,
        employee_last_name=last_name,
        email=email,
    )

    logger.info("Provisioned new Horilla user %s from Google Workspace sign-in", email)
    return user
