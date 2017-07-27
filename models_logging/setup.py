from django.db.models.signals import post_init, post_save, post_delete
from django.apps.registry import apps

from .settings import MODELS_FOR_LOGGING, MODELS_FOR_EXCLUDE
from .signals import init_model_attrs, save_model, delete_model


def models_register():
    if MODELS_FOR_LOGGING:
        registered_models = []
        for app in MODELS_FOR_LOGGING:
            item = app.split('.')
            if apps.all_models.get(item[-1]):  # if this is app
                for v in apps.get_app_config(item[-1]).models.values():
                    if '%s.%s' % (app, v.__name__) not in MODELS_FOR_EXCLUDE:
                        registered_models.append(v)
            else:   # if this is model
                registered_models.append(apps.get_registered_model(item[-2], item[-1]))

        for model in registered_models:
            post_init.connect(init_model_attrs, sender=model)
            post_save.connect(save_model, sender=model)
            post_delete.connect(delete_model, sender=model)