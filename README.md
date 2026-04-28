# Django Models Logging

This package logs every change to your Django models in the following format:

```json
{
  "field_name": {
    "old": "old_value",
    "new": "new_value"
  }
}
```

For deleted objects, `"new"` is omitted and only `"old"` is stored.

**Example:**

```json
{
  "price": {
    "old": "2425",
    "new": "645"
  },
  "name": {
    "old": "ProductName",
    "new": "NewProductName"
  }
}
```

## Requirements

- Python >= 3.10
- Django >= 5.2

## Installation

1. Install via pip:

```bash
pip install django-models-logging
```

2. Add to `INSTALLED_APPS` — must be at the **end**, after all apps whose models you want to log:

```python
INSTALLED_APPS = [
    ...,
    'models_logging',
]
```

3. Run migrations:

```bash
python manage.py migrate
```

## Configuration

### Select models to log

```python
LOGGING_MODELS = (
    'app.ClassName',  # log only this model
    'another_app',    # log all models in this app
)
```

### Exclude models from logging

```python
LOGGING_EXCLUDE = (
    'app',                # exclude all models in this app
    'another_app.Model',  # exclude a specific model
)
```

### Custom user model

If `request.user` is not your `AUTH_USER_MODEL`:

```python
LOGGING_USER_MODEL = 'yourapp.Users'
# default: AUTH_USER_MODEL
```

### Per-model field filtering

Set these as class attributes on the model:

```python
class MyModel(models.Model):
    LOGGING_IGNORE_FIELDS = ('field1', 'field2')  # exclude specific fields
    # OR
    LOGGING_ONLY_FIELDS = ('field1', 'field2')    # include only these fields
```

## Merging changes per request

By default, each `.save()` call creates a separate `Change` record. If `.save()` is called multiple times in one request, use the middleware to merge them:

```python
MIDDLEWARE = [
    ...,
    'models_logging.middleware.LoggingStackMiddleware',
]
```

To control merging independently of the middleware:

```python
LOGGING_MERGE_CHANGES = True  # default: True
```

For scripts or Celery tasks outside of a request cycle, use the context manager:

```python
from models_logging.utils import create_merged_changes

def your_task():
    with create_merged_changes():
        ...
```

To temporarily suppress logging entirely:

```python
from models_logging.utils import ignore_changes

with ignore_changes():          # ignore all models
    ...

with ignore_changes([MyModel]): # ignore specific models
    ...
```

## Logging bulk updates

`queryset.update()` does not trigger Django signals and is not logged automatically. Use `create_changes_for_update` instead:

```python
from models_logging.utils import create_changes_for_update

create_changes_for_update(MyModel.objects.filter(active=True), active=False)
```

This captures old and new values for each affected row.

## Admin

To show an object's change history in the Django admin, use `HistoryAdmin`:

```python
from models_logging.admin import HistoryAdmin

class YourModelAdmin(HistoryAdmin):
    history_latest_first = False        # show oldest first (default)
    inline_models_history = '__all__'   # '__all__' or list of inline model classes
```

### Admin permissions

```python
def can_revert(request, obj):
    return request.user.is_superuser

LOGGING_REVERT_IS_ALLOWED = can_revert   # callable or bool, default: True
LOGGING_CAN_DELETE_REVISION = False      # callable or bool, default: False
LOGGING_CAN_DELETE_CHANGES = False       # callable or bool, default: False
LOGGING_CAN_CHANGE_CHANGES = False       # callable or bool, default: False
LOGGING_CHANGES_REVISION_LIMIT = 100     # max changes shown inline in a revision
```

## Custom JSON encoder

The default encoder handles `FieldFile` and GeoDjango `Point` types. To use your own:

```python
LOGGING_JSON_ENCODER = 'path.to.your.JsonEncoder'
```

## Custom change extras

To store extra data with each change (e.g. request IP, correlation ID), provide a custom function:

```python
# yourapp/logging.py
def get_change_extras(obj, action):
    from models_logging import _local
    return {
        'ip': getattr(_local, 'request', None) and _local.request.META.get('REMOTE_ADDR'),
    }
```

```python
LOGGING_GET_CHANGE_EXTRAS_FUNC = 'yourapp.logging.get_change_extras'
```

## Management command

Delete old change records:

```bash
# delete all changes
python manage.py delete_changes

# delete changes for specific content types (by id)
python manage.py delete_changes --ctype 1,2,3

# exclude content types from deletion
python manage.py delete_changes --ctype-exclude 4,5

# delete changes older than a date
python manage.py delete_changes --date_lte 2024.01.01
```

## Version compatibility

| Package version | Django    | Python |
|---|-----------|---|
| 5.2.x | 5.2       | 3.10 – 3.14 |
| 2.x | 3.1 – 4.1 | 3.8+ |
| 0.9.7 | <= 2.0    | — |

> **Note:** This package is not a database backup solution. Reverting thousands of changes will be slow.