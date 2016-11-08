from threading import local

from django.conf import settings
from django.db.models.signals import post_init, post_save, post_delete
from django.forms.models import model_to_dict
from django.apps.registry import apps
from django.utils.encoding import force_text

from models_logging.revisions import create_changes


class _Local(local):

    def __init__(self):
        self.rev = None
        self.user = None
        self.ignore_changes = False


_local = _Local()


MODELS_FOR_LOGGING = getattr(settings, 'LOGGING_MODELS', None)
MODELS_FOR_EXCLUDE = getattr(settings, 'LOGGING_EXCLUDE', [])


def _dict(instance):
    return model_to_dict(instance, fields=[field.name for field in instance._meta.fields])


def init_model_attrs(sender, instance, **kwargs):
    instance.__attrs = _dict(instance)


def save_model(sender, instance, using, **kwargs):
    if isinstance(_local.ignore_changes, (tuple, list)) and sender in _local.ignore_changes:
        return
    elif _local.ignore_changes is True:
        return

    d1 = _dict(instance)
    d2 = instance.__attrs
    diffs = [{'field': k, 'values': (d2[k], v)} for k, v in d1.items() if v != d2[k]]
    if diffs:
        action = 'Added' if kwargs.get('created') else 'Changed'
        comment = '%(action)s %(klass)s %(repr)s:\n' % {'klass': sender.__name__, 'repr': force_text(instance),
                                                        'action': action}
        comment += '\n'.join('"%s" (%s -> %s)' % (d['field'], d['values'][0], d['values'][1]) for d in diffs)
        create_changes(instance, using, comment, action, _local.rev, _local.user)


def delete_model(sender, instance, using, **kwargs):
    if isinstance(_local.ignore_changes, (tuple, list)) and sender in _local.ignore_changes:
        return
    elif _local.ignore_changes is True:
        return
    
    comment = 'Deleted %(klass)s %(repr)s:\n' % {'klass': sender.__name__, 'repr': force_text(instance)}
    create_changes(instance, using, comment, 'Deleted', _local.rev, _local.user)


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