from django.apps import AppConfig


class AdminConfig(AppConfig):
    name = 'website'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        import website.signals  # noqa: F401
