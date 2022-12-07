from threading import local
from typing import Union, Dict, TYPE_CHECKING

from django.core.handlers.wsgi import WSGIRequest

if TYPE_CHECKING:
    from models_logging.models import Change

default_app_config = 'models_logging.apps.LoggingConfig'


class _Local(local):
    """
    :param stack_changes: all changes grouped by (object_id, content_type_id)
    it's created for grouping changes that called by multiple using of obj.save() per 1 request|operation
    """
    def __init__(self):
        self.request: "WSGIRequest" = None
        self.ignore_changes = False
        self.stack_changes: Dict[(Union[str, int], int), "Change"] = {}
        self.merge_changes_allowed = False

    def ignore(self, sender, instance) -> bool:
        if isinstance(self.ignore_changes, (tuple, list)) and sender in self.ignore_changes:
            return True
        elif self.ignore_changes is True:
            return True
        elif instance.get_deferred_fields():
            # if we do not ignore defered_fields
            # we will catch exception (max recursion depth)
            return True
        return False

    @property
    def user_id(self):
        if self.request:
            from models_logging.models import Change

            user = self.request.user
            return user.pk if user and type(user) == Change.user_field_model() and user.is_authenticated else None

    def put_change_to_stack(self, change: "Change"):
        key = (change.object_id, change.content_type.pk)
        existing_change = self.stack_changes.get(key)
        if existing_change:
            # If the object changes several times during the request, we need to properly track the changed fields
            for k, v in change.changed_data.items():
                existing_change.changed_data[k] = v
        else:
            self.stack_changes[key] = change


_local = _Local()
