import copy
from typing import Union, List

from django.db.models.base import ModelBase
from django.utils.encoding import force_str
from django.utils.module_loading import import_string

from models_logging import settings, _local
from models_logging.models import Change, Revision


def model_to_dict(instance, action=None):
    opts = instance._meta
    ignore_fields = set(getattr(instance, "LOGGING_IGNORE_FIELDS", []))
    only_fields = getattr(instance, "LOGGING_ONLY_FIELDS", [])
    if action != settings.DELETED:
        ignore_fields.update(instance.get_deferred_fields())

    fnames = [
        f.attname for f in opts.fields
        if f.name not in ignore_fields and f.attname not in ignore_fields and not only_fields or f.name in only_fields
    ]

    data = {}
    for f in fnames:
        fvalue = getattr(instance, f, None)
        if isinstance(fvalue, (list, dict)):
            fvalue = copy.deepcopy(fvalue)

        data[f] = fvalue
    return data


def get_changed_data(obj, action=settings.CHANGED):
    d1 = model_to_dict(obj, action)
    if action == settings.DELETED:
        return {k: {"old": v} for k, v in d1.items()}
    d2 = obj.__attrs
    return {
        k: {"old": d2[k] if action == settings.CHANGED else None, "new": v}
        for k, v in d1.items()
        if v != d2[k]
    }


def create_revision_with_changes(changes: List[Change]):
    """

    :param changes: _local.stack_changes
    :return:
    """
    comment = ", ".join([c.object_repr for c in changes])
    rev = Revision.objects.using(settings.LOGGING_DATABASE).create(
        comment="Changes: %s" % comment
    )
    for change in changes:
        change.revision = rev
    Change.objects.using(settings.LOGGING_DATABASE).bulk_create(changes)


def get_change_extras(object, action):
    """
    Result of this function will be stored in `Change.extras` field.
    Can be used to store additional info from `_local.request` for example:
    {
        "correlation_id": _local.request.correlation_id,    # from django_guid
        "ip": _local.request.META.get('REMOTE_ADDR')
    }
    :param: object - instance of changed model OR DICT if changes are created with `create_changes_for_update`
    """
    return {}


def init_change(
    object: Union[dict, ModelBase],
    changed_data,
    action,
    content_type,
    object_repr=None,
) -> Change:
    """
    :param object - django model or dict if it's called from create_changes_for_update
    """
    object_repr = object_repr or force_str(object)
    object_pk = object["pk"] if isinstance(object, dict) else object.pk

    if isinstance(object, Change.user_field_model()) and object_pk == _local.user_id and action == settings.DELETED:
        _local.request = None

    return Change(
        db=settings.LOGGING_DATABASE,
        object_repr=object_repr,
        action=action,
        user_id=_local.user_id,
        changed_data=changed_data,
        object_id=object_pk,
        content_type=content_type,
        extras=CHANGE_EXTRAS_FUNC(object, settings.CHANGED),
    )


CHANGE_EXTRAS_FUNC = import_string(settings.GET_CHANGE_EXTRAS_PATH)
