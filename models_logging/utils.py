# Helpers
from .settings import DELETED, CHANGED


def model_to_dict(instance, action=None):
    def fname(f):
        return '%s_id' % f.name if f.is_relation else f.name

    opts = instance._meta
    ignore_fields = getattr(instance, 'LOGGING_IGNORE_FIELDS', [])
    only_fields = getattr(instance, 'LOGGING_ONLY_FIELDS', [])
    if action != DELETED and only_fields:
        fnames = [fname(f) for f in opts.fields if f.name in only_fields]
    elif action != DELETED and ignore_fields:
        fnames = [fname(f) for f in opts.fields if f.name not in ignore_fields]
    else:
        fnames = [fname(f) for f in opts.fields]
    data = {f: getattr(instance, f, None) for f in fnames}
    return data


def get_changed_data(obj, action=CHANGED):
    d1 = model_to_dict(obj, action)
    if action == DELETED:
        return [{'field': k, 'values': {'old': v}} for k, v in d1.items()]
    else:
        d2 = obj.__attrs
        return [
            {
                'field': k,
                'values': {'old': d2[k] if action == CHANGED else None, 'new': v}
            } for k, v in d1.items() if v != d2[k]
        ]