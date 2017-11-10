# Helpers
from contextlib import contextmanager

from . import _local
from .settings import DELETED, CHANGED
from .models import Revision, Change


def model_to_dict(instance, action=None):
    def fname(f):
        return '%s_id' % f.name if f.is_relation else f.name

    opts = instance._meta
    ignore_fields = getattr(instance, 'LOGGING_IGNORE_FIELDS', [])
    only_fields = getattr(instance, 'LOGGING_ONLY_FIELDS', [])
    if action != DELETED and only_fields:
        fnames = [fname(f) for f in opts.fields if f.name in only_fields]
    elif action != DELETED and ignore_fields:
        fnames = [fname(f) for f in opts.fields if f.name not in ignore_fields]
    else:
        fnames = [fname(f) for f in opts.fields]
    data = {f: getattr(instance, f, None) for f in fnames}
    return data


def get_changed_data(obj, action=CHANGED):
    d1 = model_to_dict(obj, action)
    if action == DELETED:
        return [{'field': k, 'values': {'old': v}} for k, v in d1.items()]
    else:
        d2 = obj.__attrs
        return [
            {
                'field': k,
                'values': {'old': d2[k] if action == CHANGED else None, 'new': v}
            } for k, v in d1.items() if v != d2[k]
        ]


@contextmanager
def ignore_changes(models=None):
    """

    :param models: tuple or list of django models instances or bool if you want to ignore all changes
    :return:
    """
    if models:
        assert isinstance(models, (tuple, list, bool))
    _local.ignore_changes = models or True
    yield
    _local.ignore_changes = False


@contextmanager
def create_merged_changes():
    """

    :param changes: list of changes from create_changes,
    can be empty if we want use models_logging functional from third part scripts
    :return:
    """
    _local.stack_changes = {}
    yield
    create_revision_with_changes(_local.stack_changes.values())


def create_revision_with_changes(changes):
    """

    :param changes: _local.stack_changes
    :return:
    """
    comment = ', '.join([v['object_repr'] for v in changes])
    rev = Revision.objects.create(comment='Изменения %s' % comment)
    bulk = []
    for data in changes:
        data['revision_id'] = rev.id
        bulk.append(Change(**data))
    Change.objects.bulk_create(bulk)