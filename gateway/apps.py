from django.apps import AppConfig


class GatewayConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gateway"

    def ready(self):
        from gateway import schema  # noqa: F401
