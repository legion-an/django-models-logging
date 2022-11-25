from contextlib import contextmanager

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.fields.files import FieldFile

from models_logging import _local, settings
from models_logging.helpers import create_revision_with_changes, init_change
from models_logging.models import Change

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
    _local.merge_changes_allowed = True

    yield

    create_revision_with_changes(_local.stack_changes.values())

    _local.stack_changes = {}
    _local.merge_changes_allowed = False


def create_changes_for_update(queryset, **fields):
    def _get_values(qs):
        return {item["pk"]: item for item in qs.values("pk", *fields)}

    old_values = _get_values(queryset)
    rows = queryset.update(**fields)
    new_values = _get_values(queryset.model.objects.filter(id__in=old_values.keys()))

    content_type = ContentType.objects.get_for_model(queryset.model)

    changes = []
    for pk, item in old_values.items():
        changed_data = {
            field: {"old": old_value, "new": new_values[pk][field]}
            for field, old_value in item.items() if field != 'pk'
        }
        changes.append(
            init_change(
                item,
                changed_data,
                settings.CHANGED,
                content_type,
                f"Update of {queryset.model.__name__} (pk={pk})",
            )
        )

    if settings.MERGE_CHANGES and _local.merge_changes_allowed:
        for change in changes:
            _local.put_change_to_stack(change)
    else:
        Change.objects.using(settings.LOGGING_DATABASE).bulk_create(changes)

    return rows
