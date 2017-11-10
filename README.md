# Add 'models_logging' at the end of INSTALLED_APPS!
# This is important because models connect to save and init
# signals when apps is ready

# 1.
```
#!python

INSTALLED_APPS = (
    ...,
    'models_logging',
)
```

# 2. make migrations

# 3. add models you want to logging in settings, format:

```
#!python

LOGGING_MODELS = (
    'app.ClassName',    # logging only for this model
    'another_app'     # logging of all models in this app
)
```

# In many applications object.save() operation can be called many times per 1 request
# per each .save() models_logging creates Change, so your database can fast raise to very huge size
# for prevent this "bug" you can add middleware in settings
```
#!python

MIDDLEWARE_CLASSES = (
    ...,
    'models_logging.middleware.LoggingStackMiddleware',     # it merge all changes of object per request
)
```

# or use context_manager from models_logging.utils in your view or script
```
#!python
from models_logging.utils import create_merged_changes


def your_script():
    with create_merged_changes():
        ...
```


# You can add model for ignore logging
```
#!python

LOGGING_EXCLUDE = (
    'app'     # ignore logging of all models in this app
    'another_app.Model'     # ignore logging for this model
)
```


# Also you can set up permission to logging records
# Make func (it will be called in admin) or bool

```
#!python

def can_revert(request, obj):
    return request.user.username == 'myusername'

LOGGING_REVERT_IS_ALLOWED = can_revert
LOGGING_CAN_DELETE_REVISION = can_revert
LOGGING_CAN_DELETE_CHANGES = False
LOGGING_CAN_CHANGE_CHANGES = True
```

# in models you can set attributes:
 ```
#!python
LOGGING_IGNORE_FIELDS   # to ignore changes of some fields

#OR

LOGGING_ONLY_FIELDS     # to save changes of only those fields 
```
 
 
# If you want to watch changes in admin/history of your object you can use models_logging.admin.HistoryAdmin

 ```
#!python
from models_logging.admin import HistoryAdmin


class YourAdminModel(HistoryAdmin):
    history_latest_first = False    # latest changes first
    inline_models_history = '__all__'   # __all__ or list of inline models for this ModelAdmin

```



# PS: It's not a backup your database, don't try to revert "huge" Revisions
# Recovering changes it's at least 1 hit to database (save or delete),
# if you run recovering thousands of changes this will be very slowly