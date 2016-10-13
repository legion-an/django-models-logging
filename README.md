# Add 'models_logging' at the end of INSTALLED_APPS!
# This is important because models connect to save and init
# signals when apps is ready
```
#!python

INSTALLED_APPS = (
    ...,
    'models_logging',
)
```

# make migrations

# set models you want to logging in settings, format:

```
#!python

LOGGING_MODELS = (
    'app.ClassName',    # logging only for this model
    'another_app'     # logging of all models in this app
)
```

# You can set model for ignore logging
```
#!python

LOGGING_MODELS = (
    'another_app.Model'     # logging of all models in this app
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