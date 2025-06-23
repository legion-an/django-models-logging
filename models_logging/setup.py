from django.db.models.signals import post_init, post_save, pre_delete, pre_save
from django.apps.registry import apps

from .settings import MODELS_FOR_LOGGING, MODELS_FOR_EXCLUDE
from .signals import init_model_attrs, save_model, delete_model, update_model_attrs


def models_register():
    registered_models = []
    if MODELS_FOR_LOGGING:
        for app in MODELS_FOR_LOGGING:
            item = app.split('.')
            if item[-1] in [app_config.label for app_config in apps.get_app_configs()]:
                # If item is an app, register all models
                for v in apps.get_app_config(item[-1]).models.values():
                    if '%s.%s' % (app, v.__name__) not in MODELS_FOR_EXCLUDE:
                        registered_models.append(v)
            else:
                # If the item is a single model, register it
                registered_models.append(apps.get_registered_model(item[-2], item[-1]))

        for model in registered_models:
            post_init.connect(init_model_attrs, sender=model)
            pre_save.connect(update_model_attrs, sender=model)
            post_save.connect(save_model, sender=model)
            pre_delete.connect(delete_model, sender=model)

    return registered_models
