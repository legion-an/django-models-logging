from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LoggingConfig(AppConfig):
    name = 'models_logging'
    verbose_name = _('Models logging')
    default_auto_field = "django.db.models.AutoField"

    def ready(self):
        from .setup import models_register
        models_register()
