from django.conf import settings
from django.utils.module_loading import import_string

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object

from . import _local
from .settings import MERGE_CHANGES
from .utils import create_revision_with_changes


class LoggingStackMiddleware(MiddlewareMixin):

    def process_request(self, request):
        _local.stack_changes = {}
        _local.request = request
        _local.merge_changes_allowed = MERGE_CHANGES_ALLOWED

    def process_response(self, request, response):
        if MERGE_CHANGES and _local.stack_changes:
            self.create_revision(_local)
        return response

    def create_revision(self, _local):
        # this method for overriding and call create_revision_with_changes async maybe

        create_revision_with_changes(_local.stack_changes.values())
        _local.stack_changes = {}


MERGE_CHANGES_ALLOWED = False
for middleware in settings.MIDDLEWARE:
    middleware_cls = import_string(middleware)(None)

    if isinstance(middleware_cls, LoggingStackMiddleware):
        MERGE_CHANGES_ALLOWED = True
        break
