from threading import local


default_app_config = 'models_logging.apps.LoggingConfig'


class _Local(local):
    """
    :param stack_changes: all changes grouped by (object_id, content_type_id)
    it's created for grouping changes that called by multiple using of obj.save() per 1 request|operation
    """
    def __init__(self):
        self.user = None
        self.ignore_changes = False
        self.stack_changes = {}

    def ignore(self, sender, instance):
        if isinstance(self.ignore_changes, (tuple, list)) and sender in self.ignore_changes:
            return True
        elif self.ignore_changes is True:
            return True
        elif instance.get_deferred_fields():
            # if does'nt ignore defered_fields
            # we will catch excpetion (max recursion depth)
            return True


_local = _Local()