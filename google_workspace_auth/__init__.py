"""
google_workspace_auth/__init__.py

"Sign in with Google", restricted to a single Google Workspace domain.

Setup:
  1. In Google Cloud Console, create an OAuth 2.0 Client ID (Web application)
     for the project tied to your Workspace. Add
     https://<your-domain>/google/callback/ as an authorized redirect URI.
  2. In Django admin, add a "Google Workspace Settings" row with that
     client ID/secret, the same redirect URI, your Workspace domain (e.g.
     yourcompany.com), and tick "Enabled".
  3. The "Sign in with Google" button then appears on the login page.

NOTE: Horilla should be run behind HTTPS -- Google will not redirect to a
plain http:// callback in production, and this app assumes https when it
rebuilds the callback URL.

A user removed/suspended in Google Workspace is blocked automatically: the
OAuth flow itself fails for them at Google, before this app ever runs. This
app does not poll the Workspace Admin SDK, so an already-open Horilla
session for someone removed from Workspace is not force-ended -- it just
runs out at its normal session expiry, same as any other login.
"""
