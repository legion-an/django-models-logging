try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object

from . import _local
from .settings import MERGE_CHANGES
from .utils import create_revision_with_changes


class LoggingStackMiddleware(MiddlewareMixin):

    def process_request(self, request):
        _local.user = request.user

    def process_response(self, request, response):
        if MERGE_CHANGES and _local.stack_changes:
            self.create_revision(_local)
        return response
    
    def create_revision(self, _local):
        # this method for overriding and call create_revision_with_changes async maybe

        create_revision_with_changes(_local.stack_changes.values())
        _local.stack_changes = {}