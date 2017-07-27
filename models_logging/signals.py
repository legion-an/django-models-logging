import json
from threading import local
from contextlib import contextmanager

from django.utils.encoding import force_text
from django.core.serializers.json import DjangoJSONEncoder

from .utils import get_changed_data, model_to_dict
from .settings import ADDED, CHANGED, DELETED


class _Local(local):

    def __init__(self):
        self.rev = None
        self.user = None
        self.ignore_changes = False


_local = _Local()


def init_model_attrs(sender, instance, **kwargs):
    if isinstance(_local.ignore_changes, (tuple, list)) and sender in _local.ignore_changes:
        return
    elif _local.ignore_changes is True:
        return
    elif instance.get_deferred_fields():
        # if does'nt ignore defered_fields
        # we will catch excpetion (max recursion depth)
        return

    instance.__attrs = model_to_dict(instance)


def save_model(sender, instance, using, **kwargs):
    if isinstance(_local.ignore_changes, (tuple, list)) and sender in _local.ignore_changes:
        return
    elif _local.ignore_changes is True:
        return
    elif instance.get_deferred_fields():
        return

    diffs = get_changed_data(instance)
    if diffs:
        action = ADDED if kwargs.get('created') else CHANGED
        create_changes(instance, using, action, _local.rev, _local.user)


def delete_model(sender, instance, using, **kwargs):
    if isinstance(_local.ignore_changes, (tuple, list)) and sender in _local.ignore_changes:
        return
    elif _local.ignore_changes is True:
        return
    elif instance.get_deferred_fields():
        return

    create_changes(instance, using, DELETED, _local.rev, _local.user)


def create_changes(object, using, action, rev=None, user=None):
    from models_logging.models import Change
    data = json.dumps(get_changed_data(object, action), cls=DjangoJSONEncoder)
    Change.objects.create(object=object, db=using, changed_data=data, object_repr=force_text(object), action=action,
                          revision=rev, user=user)


@contextmanager
def create_revision(rev=None, user=None, ignore_changes=False):
    _local.rev = rev
    _local.user = user
    _local.ignore_changes = ignore_changes
    yield
    _local.rev = None
    _local.user = None
    _local.ignore_changes = False