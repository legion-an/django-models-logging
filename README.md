# This package is for logging every changes in your models in this format:
```json

[{"field": "price", "values": {"old": "2425", "new": "645"}}, {"field": "price_final", "values": {"old": "2425", "new": "645"}}]
```

# USING
Add 'models_logging' at the end of INSTALLED_APPS in settings.py!
This is important because models connect to save and init signals when apps is ready

1.
```python
INSTALLED_APPS = (
    ...,
    'models_logging',
)
```

If request.user is not represented by AUTH_USER_MODEL in your application then you can set up a custom Users model:

```python
LOGGING_USER_MODEL = 'yourapp.Users'
# By default, LOGGING_USER_MODEL = AUTH_USER_MODEL
```



2. make migrations
3. add the models you want to log in settings.py, format:
```python
LOGGING_MODELS = (
    'app.ClassName',    # logging only for this model
    'another_app'     # logging of all models in this app
)
```

Sometimes object.save() operation can be called many times per 1 request.
Per each .save() models_logging creates Change, so your database can quickly grow to a very large size
for prevent this "bug" you can add middleware in settings.py
```python
MIDDLEWARE = (
    ...,
    'models_logging.middleware.LoggingStackMiddleware',     # it merge all changes of object per request
)
```

or use context_manager from models_logging.utils in your view or script
```python
from models_logging.utils import create_merged_changes

def your_script():
    with create_merged_changes():
        ...
```


You can add model for ignore logging
settings.py
```python
LOGGING_EXCLUDE = (
    'app'     # ignore logging of all models in this app
    'another_app.Model'     # ignore logging for this model
)
```


Also you can set up permission for the logging records
Make func (it will be called in admin) or bool
settings.py
```python
def can_revert(request, obj):
    return request.user.username == 'myusername'

LOGGING_REVERT_IS_ALLOWED = can_revert
LOGGING_CAN_DELETE_REVISION = can_revert
LOGGING_CAN_DELETE_CHANGES = False
LOGGING_CAN_CHANGE_CHANGES = True
```

in models you can set attributes:
```python
LOGGING_IGNORE_FIELDS = ()  # to ignore changes of some fields

# OR

LOGGING_ONLY_FIELDS  = ()    # to save changes of only those fields 
```
 
 
If you want to watch changes in admin/history of your object you can use models_logging.admin.HistoryAdmin
```python
from models_logging.admin import HistoryAdmin


class YourAdminModel(HistoryAdmin):
    history_latest_first = False    # latest changes first
    inline_models_history = '__all__'   # __all__ or list of inline models for this ModelAdmin

```

If you want to exclude some actions from being logged in order to save storage or for some other reasons then you can attach a meta-class Logging and set the following attributes: 
- ignore_on_create (False by default. Skips logging of `create` actions)
- ignore_on_update (False by default. Skips logging of `update` actions)

```python
from django.db import models

class YourModel(models.Model):
    name = models.CharField(max_length=1000)
    
    class Logging:
        ignore_on_create = True
        ignore_on_update = True
```
Please note, setting up *ignore_on_...* as True will cause impossibility of reverting your data.



Version > 1.0 is incompatible with old versions (requires django >= 2.0)
for django <= 2.0 use 0.9.7 version
 


PS: It's not a backup your database, don't try to revert "huge" Revisions
Recovering changes it's at least 1 hit to database (save or delete),
if you run recovering thousands of changes this will be very slowly