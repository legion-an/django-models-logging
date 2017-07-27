from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class LoggingConfig(AppConfig):
    name = 'models_logging'
    verbose_name = _('Models logging')

    def ready(self):
        from .setup import models_register
        models_register()