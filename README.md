# Django Models Logging

This package is for logging every changes in your models in this format:

```yaml
{
    field_name: {
        "old":  `old_value`, "new":  `new_value` | `None` if this is delete action
    }
}
```

Example

```json
{
  "price": {
    "old": "2425",
    "new": "645"
  },
  "name": {
    "old": "ProductName",
    "new": "NewProductNmae"
  }
}
```

# USING

Add 'models_logging' at the end of INSTALLED_APPS in settings.py!
This is important because models connect to save and init signals when apps is ready

1. Install using pip - `pip install django-models-logging`

2.

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

3. make migrations
4. add the models you want to log in settings.py, format:

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

You can implement your own JSONEncoder and set path to it in django settings

```python
LOGGING_JSON_ENCODER = 'path.to.your.JsonEncoder'
```

> Version > 1.0 is incompatible with old versions (requires django >= 2.0)
> For django <= 2.0 use 0.9.7 version
> Version > 2.0 is incompatible with old versions (requires django >= 3.1)

PS: This module is not optimal as a backup for your database. If you try to recover thousands of changes this will be very slow.
