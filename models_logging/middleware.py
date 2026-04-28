from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.utils.module_loading import import_string

from models_logging import _local
from models_logging.settings import MERGE_CHANGES
from models_logging.utils import create_revision_with_changes


class LoggingStackMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.stack_changes = {}
        _local.request = request
        _local.merge_changes_allowed = MERGE_CHANGES_ALLOWED

        response = self.get_response(request)

        if MERGE_CHANGES and _local.stack_changes:
            self.create_revision(_local)

        return response

    @staticmethod
    def create_revision(_local):
        # use a dedicated method to be able to override it and call create_revision_with_changes async

        create_revision_with_changes(_local.stack_changes.values())
        _local.stack_changes = {}


MERGE_CHANGES_ALLOWED = False
for middleware in settings.MIDDLEWARE:
    try:
        middleware_cls = import_string(middleware)(object)
    except MiddlewareNotUsed:
        continue

    if isinstance(middleware_cls, type) and issubclass(
        middleware_cls, LoggingStackMiddleware
    ):
        MERGE_CHANGES_ALLOWED = True
        break
