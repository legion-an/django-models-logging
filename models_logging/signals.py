from django.contrib.contenttypes.models import ContentType

from . import _local
from .helpers import model_to_dict, get_changed_data, init_change
from .settings import ADDED, CHANGED, DELETED, MERGE_CHANGES, LOGGING_DATABASE


def init_model_attrs(sender, instance, **kwargs):
    if not _local.ignore(sender, instance):
        model_dict = model_to_dict(instance)
        # for rest_framework
        if not instance.pk:
            model_dict = {k: None for k, v in model_dict.items()}

        instance.__attrs = model_dict


def save_model(sender, instance, using, **kwargs):
    if not _local.ignore(sender, instance):
        diffs = get_changed_data(instance)
        if diffs:
            action = ADDED if kwargs.get('created') else CHANGED
            _create_changes(instance, action)


def delete_model(sender, instance, using, **kwargs):
    if not _local.ignore(sender, instance):
        _create_changes(instance, DELETED)


def _create_changes(object, action):
    changed_data = get_changed_data(object, action)

    change = init_change(
        object,
        changed_data,
        action,
        ContentType.objects.get_for_model(object._meta.model)
    )

    if MERGE_CHANGES and _local.merge_changes_allowed:
        _local.put_change_to_stack(change)
    else:
        change.save(using=LOGGING_DATABASE)


def update_model_attrs(signal, sender, instance, **kwargs):
    if not _local.ignore(sender, instance):
        # if there are deferred fields which are changed still, we need to get old values from the DB
        if instance.get_deferred_fields():
            new_values = model_to_dict(instance)
            if missed_fields := (set(new_values).difference(instance.__attrs)):
                instance.refresh_from_db(fields=missed_fields)
                for k in missed_fields:
                    # Update __attrs with fields from the DB (old values)
                    instance.__attrs[k] = getattr(instance, k)
                    # set new values again
                    setattr(instance, k, new_values[k])
