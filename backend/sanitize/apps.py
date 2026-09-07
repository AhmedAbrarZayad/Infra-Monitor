from django.apps import AppConfig


class SanitizeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sanitize"
    verbose_name = "Request Shield (Sanitize)"
