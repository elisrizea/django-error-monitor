from django.apps import AppConfig


class AiMonitoringConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ai_monitoring"
    verbose_name = "Error Monitoring"

    def ready(self):
        # Importing the module registers its @register()-decorated system checks.
        from . import checks  # noqa: F401
