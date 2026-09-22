"""
google_workspace_auth/models.py
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class GoogleWorkspaceSettings(models.Model):
    """
    Configuration for "Sign in with Google" restricted to a single Google
    Workspace domain.

    A user's Google account has to still exist and be active in the
    Workspace for the OAuth flow to complete at all -- Google itself refuses
    to authenticate a deleted/suspended account, so removing someone from
    Workspace is what blocks their next Horilla login. This app never talks
    to the Admin SDK; it only relies on that Google-side behavior plus the
    `hd` (hosted domain) claim on the verified ID token.
    """

    is_enabled = models.BooleanField(
        default=False,
        verbose_name=_("Enabled"),
        help_text=_("Show 'Sign in with Google' on the login page."),
    )
    client_id = models.CharField(
        max_length=255,
        verbose_name=_("OAuth Client ID"),
        help_text=_("From Google Cloud Console -> APIs & Services -> Credentials."),
    )
    client_secret = models.CharField(
        max_length=255,
        verbose_name=_("OAuth Client Secret"),
    )
    redirect_uri = models.CharField(
        max_length=255,
        verbose_name=_("Redirect URI"),
        help_text=_(
            "Must exactly match an authorized redirect URI on the OAuth client, "
            "e.g. https://hr.yourcompany.com/google/callback/"
        ),
    )
    allowed_domain = models.CharField(
        max_length=255,
        verbose_name=_("Workspace domain"),
        help_text=_(
            "Only Google accounts on this Workspace domain may sign in, "
            "e.g. yourcompany.com."
        ),
    )
    auto_create_employee = models.BooleanField(
        default=True,
        verbose_name=_("Auto-create employees"),
        help_text=_(
            "Create a new Horilla user/employee automatically the first time "
            "someone signs in with Google. When off, only emails that already "
            "match an existing Horilla user may sign in this way."
        ),
    )

    class Meta:
        verbose_name = _("Google Workspace Settings")
        verbose_name_plural = _("Google Workspace Settings")

    def __str__(self):
        return f"Google Workspace SSO ({self.allowed_domain})"
