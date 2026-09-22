"""
google_workspace_auth/admin.py
"""

from django.contrib import admin

from google_workspace_auth.models import GoogleWorkspaceSettings

admin.site.register(GoogleWorkspaceSettings)
