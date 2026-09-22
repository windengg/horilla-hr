# Generated manually to match Django 5.2's `makemigrations` output for this
# app -- run `manage.py makemigrations --check google_workspace_auth` after
# installing to confirm it still matches the models as written.

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="GoogleWorkspaceSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "is_enabled",
                    models.BooleanField(
                        default=False,
                        help_text="Show 'Sign in with Google' on the login page.",
                        verbose_name="Enabled",
                    ),
                ),
                (
                    "client_id",
                    models.CharField(
                        help_text="From Google Cloud Console -> APIs & Services -> Credentials.",
                        max_length=255,
                        verbose_name="OAuth Client ID",
                    ),
                ),
                (
                    "client_secret",
                    models.CharField(max_length=255, verbose_name="OAuth Client Secret"),
                ),
                (
                    "redirect_uri",
                    models.CharField(
                        help_text=(
                            "Must exactly match an authorized redirect URI on the "
                            "OAuth client, e.g. "
                            "https://hr.yourcompany.com/google/callback/"
                        ),
                        max_length=255,
                        verbose_name="Redirect URI",
                    ),
                ),
                (
                    "allowed_domain",
                    models.CharField(
                        help_text=(
                            "Only Google accounts on this Workspace domain may "
                            "sign in, e.g. yourcompany.com."
                        ),
                        max_length=255,
                        verbose_name="Workspace domain",
                    ),
                ),
                (
                    "auto_create_employee",
                    models.BooleanField(
                        default=True,
                        help_text=(
                            "Create a new Horilla user/employee automatically the "
                            "first time someone signs in with Google. When off, "
                            "only emails that already match an existing Horilla "
                            "user may sign in this way."
                        ),
                        verbose_name="Auto-create employees",
                    ),
                ),
            ],
            options={
                "verbose_name": "Google Workspace Settings",
                "verbose_name_plural": "Google Workspace Settings",
            },
        ),
    ]
