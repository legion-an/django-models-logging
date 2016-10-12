# Add 'models_logging' into INSTALLED_APPS
# make migrations

# set models you want to logging in settings, format:

```
#!python

LOGGING_MODELS = (
    'app.ClassName',    # logging only for this model
    'another_app'     # logging of all models in this app
)
```


# Also you can setup permission to logging records
# You can make func (she called in admin) or bool

```
#!python

def can_revert(request, obj):
    return request.user.username == 'myusername'

LOGGING_REVERT_IS_ALLOWED = can_revert
LOGGING_CAN_DELETE_REVISION = can_revert
LOGGING_CAN_DELETE_CHANGES = False
LOGGING_CAN_CHANGE_CHANGES = True
```

# In the end of settings file

```
#!python

import models_logging
models_logging.models_register()
```