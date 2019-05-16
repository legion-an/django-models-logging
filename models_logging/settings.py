from django.conf import settings

LOGGING_USER_MODEL = getattr(settings, 'LOGGING_USER_MODEL', None) or getattr(settings, 'AUTH_USER_MODEL', None)

MODELS_FOR_LOGGING = getattr(settings, 'LOGGING_MODELS', None)
MODELS_FOR_EXCLUDE = getattr(settings, 'LOGGING_EXCLUDE', [])


REVERT_IS_ALLOWED = getattr(settings, 'LOGGING_REVERT_IS_ALLOWED', True)
CAN_DELETE_REVISION = getattr(settings, 'LOGGING_CAN_DELETE_REVISION', False)
CAN_DELETE_CHANGES = getattr(settings, 'LOGGING_CAN_DELETE_CHANGES', False)
CAN_CHANGE_CHANGES = getattr(settings, 'LOGGING_CAN_CHANGE_CHANGES', False)
CHANGES_REVISION_LIMIT = getattr(settings, 'LOGGING_CHANGES_REVISION_LIMIT', 100)
MERGE_CHANGES = getattr(settings, 'LOGGING_MERGE_CHANGES', True)

ADDED = 'added'
CHANGED = 'changed'
DELETED = 'deleted'

CUSTOM_JSON_ENCODER = getattr(settings, 'CUSTOM_JSON_ENCODER', None)

MIDDLEWARES = settings.MIDDLEWARE