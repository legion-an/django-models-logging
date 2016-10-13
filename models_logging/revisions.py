from django.core.serializers import serialize
from django.utils.encoding import force_text
from contextlib import contextmanager


def create_changes(object, using, comment, action, rev=None, user=None):
    from models_logging.models import Changes
    Changes.objects.create(object=object, db=using, serialized_data=serialize('json', (object,)),
                           object_repr=force_text(object), comment=comment, action=action, revision=rev, user=user)


@contextmanager
def create_revision(rev=None, user=None):
    from models_logging.signals import _local
    _local.rev = rev
    _local.user = user
    yield
    _local.rev = None
    _local.user = None