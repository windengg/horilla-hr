"""
google_workspace_auth/apps.py
"""

from django.apps import AppConfig


class GoogleWorkspaceAuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "google_workspace_auth"
    verbose_name = "Google Workspace Sign-in"

    def ready(self):
        from horilla.urls import include, path, urlpatterns

        urlpatterns.append(
            path("google/", include("google_workspace_auth.urls")),
        )
        return super().ready()
