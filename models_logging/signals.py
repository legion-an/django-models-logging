import json

from django.utils.encoding import force_text
from django.contrib.contenttypes.models import ContentType
from django.utils.module_loading import import_string

from . import _local
from .utils import get_changed_data, model_to_dict, ExtendedEncoder
from .settings import ADDED, CHANGED, DELETED, MERGE_CHANGES, MIDDLEWARES
from .models import Change
from .settings import CUSTOM_JSON_ENCODER


JSON_ENCODER = ExtendedEncoder
if CUSTOM_JSON_ENCODER:
    JSON_ENCODER = import_string(CUSTOM_JSON_ENCODER)


def init_model_attrs(sender, instance, **kwargs):
    if not _local.ignore(sender, instance):
        model_dict = model_to_dict(instance)
        # for rest_framework
        if not instance.id:
            model_dict = {k: None for k, v in model_dict.items()}

        instance.__attrs = model_dict


def save_model(sender, instance, using, **kwargs):
    if not _local.ignore(sender, instance):
        diffs = get_changed_data(instance)
        if diffs:
            action = ADDED if kwargs.get('created') else CHANGED
            _create_changes(instance, using, action)


def delete_model(sender, instance, using, **kwargs):
    if not _local.ignore(sender, instance):
        _create_changes(instance, using, DELETED)


def _create_changes(object, using, action):
    changed_data = json.dumps(get_changed_data(object, action), cls=JSON_ENCODER)
    user_id = _local.user.pk if _local.user and _local.user.is_authenticated else None
    content_type_id = ContentType.objects.get_for_model(object._meta.model).pk
    data = {'db': using, 'object_repr': force_text(object), 'action': action, 'user_id': user_id,
            'changed_data': changed_data, 'object_id': object.pk, 'content_type_id': content_type_id}
    if MERGE_CHANGES and 'models_logging.middleware.LoggingStackMiddleware' in MIDDLEWARES:
        key = (object.pk, content_type_id)
        old_action = _local.stack_changes.get(key, {}).get('action')
        if old_action == ADDED:
            data['action'] = ADDED
        _local.stack_changes[key] = data
    else:
        Change.objects.create(**data)