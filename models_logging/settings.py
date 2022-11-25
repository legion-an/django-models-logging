from django.conf import settings
from django.utils.module_loading import import_string


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

MIDDLEWARES = settings.MIDDLEWARE

# TODO: Is not completed feature, do not use it!
#  It will prevent error in database if User is not in the same database (because of ForeignKey)
LOGGING_DATABASE = getattr(settings, 'LOGGING_DATABASE', 'default')

JSON_ENCODER_PATH = getattr(settings, 'LOGGING_JSON_ENCODER', 'models_logging.utils.ExtendedEncoder')
JSON_ENCODER = import_string(JSON_ENCODER_PATH)

GET_CHANGE_EXTRAS_PATH = getattr(
    settings,
    'LOGGING_GET_CHANGE_EXTRAS_FUNC',
    'models_logging.utils.get_change_extras'
)
GET_CHANGE_EXTRAS_FUNC = import_string(GET_CHANGE_EXTRAS_PATH)
