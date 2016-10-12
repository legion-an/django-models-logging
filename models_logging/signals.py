from threading import local

import django
from django.conf import settings
from django.db.models.signals import post_init, post_save, post_delete
from django.forms.models import model_to_dict
from django.apps.registry import apps
from django.utils.encoding import force_text

from models_logging.revisions import create_changes


class _Local(local):

    def __init__(self):
        self.rev = None


_local = _Local()


MODELS_FOR_LOGGING = getattr(settings, 'LOGGING_MODELS', None)


def _dict(instance):
    return model_to_dict(instance, fields=[field.name for field in instance._meta.fields])


def init_model_attrs(sender, instance, **kwargs):
    instance.__attrs = _dict(instance)


def save_model(sender, instance, using, **kwargs):
    d1 = _dict(instance)
    d2 = instance.__attrs
    diffs = [{'field': k, 'values': (d2[k], v)} for k, v in d1.items() if v != d2[k]]
    if diffs:
        action = 'Added' if kwargs.get('created') else 'Changed'
        comment = '%(action)s %(klass)s %(repr)s:\n' % {'klass': sender.__name__, 'repr': force_text(instance),
                                                        'action': action}
        comment += '\n'.join('field "%s" (%s -> %s)' % (d['field'], d['values'][0], d['values'][1]) for d in diffs)
        create_changes(instance, using, comment, action, _local.rev)


def delete_model(sender, instance, using, **kwargs):
    comment = 'Deleted %(klass)s %(repr)s:\n' % {'klass': sender.__name__, 'repr': force_text(instance)}
    create_changes(instance, using, comment, 'Deleted', _local.rev)


def models_register():
    if MODELS_FOR_LOGGING:
        django.setup()
        registered_models = []
        for app in MODELS_FOR_LOGGING:
            model = app.split('.')
            if apps.all_models.get(model[-1]):  # if this is app
                registered_models += apps.get_app_config(model[-1]).models.values()
            else:   # if this is model
                registered_models.append(apps.get_registered_model(model[-2], model[-1]))

        for model in registered_models:
            post_init.connect(init_model_attrs, sender=model)
            post_save.connect(save_model, sender=model)
            post_delete.connect(delete_model, sender=model)