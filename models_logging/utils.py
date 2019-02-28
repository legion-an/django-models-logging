# Helpers
from contextlib import contextmanager

from django.core.exceptions import ImproperlyConfigured
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.fields.files import FieldFile

from . import _local
from .settings import DELETED, CHANGED
from .models import Revision, Change

try:
    from django.contrib.gis.geos import Point

    GEOS_POINT = True
except ImproperlyConfigured:
    GEOS_POINT = False


class ExtendedEncoder(DjangoJSONEncoder):

    def default(self, o):
        if GEOS_POINT and isinstance(o, Point):
            return {'type': o.geom_type, 'coordinates': [*o.coords]}
        if isinstance(o, FieldFile):
            return getattr(o, 'name', None)
        return super(ExtendedEncoder, self).default(o)


def model_to_dict(instance, action=None):
    opts = instance._meta
    ignore_fields = getattr(instance, 'LOGGING_IGNORE_FIELDS', [])
    only_fields = getattr(instance, 'LOGGING_ONLY_FIELDS', [])
    if action != DELETED and only_fields:
        fnames = [f.attname for f in opts.fields if f.name in only_fields]
    elif action != DELETED and ignore_fields:
        fnames = [f.attname for f in opts.fields if f.name not in ignore_fields]
    else:
        fnames = [f.attname for f in opts.fields]
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

    :param models: tuple or list of django models or bool if you want to ignore all changes
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
    for using merged changes in some script outside django (ex. celery)
    @task
    def some_task():
        with create_merged_changes():
            some logic

    first clean _local.stack_changes
    in your logic, changes appended to _local.stack_changes
    at the end all changes will be added in database
    :return:
    """
    _local.stack_changes = {}
    yield
    create_revision_with_changes(_local.stack_changes.values())
    _local.stack_changes = {}


def create_revision_with_changes(changes):
    """

    :param changes: _local.stack_changes
    :return:
    """
    comment = ', '.join([v['object_repr'] for v in changes])
    rev = Revision.objects.create(comment='Changes: %s' % comment)
    bulk = []
    for data in changes:
        data['revision_id'] = rev.id
        bulk.append(Change(**data))
    Change.objects.bulk_create(bulk)
