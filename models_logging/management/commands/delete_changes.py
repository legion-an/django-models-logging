from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from models_logging.models import Change, Revision


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--ctype",
            type=str,
            help="ids by comma of content_types which will be deleted",
        )
        parser.add_argument(
            "--ctype-exclude",
            type=str,
            help="ids by comma of content_types which will be excluded from deletion",
        )
        parser.add_argument(
            "--older-than",
            type=int,
            help="The changes older than N days",
        )

    def handle(self, *args, **options):
        content_type = options["ctype"]
        older_than = options["older_than"]
        ctype_exclude = options["ctype_exclude"]

        changes = Change.objects.all()
        if content_type:
            changes = changes.filter(content_type__id__in=content_type.split(","))
        if ctype_exclude:
            changes = changes.exclude(content_type__id__in=ctype_exclude.split(","))
        if older_than:
            changes = changes.filter(
                date_created__lte=timezone.now() - timedelta(older_than)
            )

        deleted = changes._raw_delete("default")
        self.stdout.write(f"{deleted} Changes have been deleted")

        deleted = Revision.objects.filter(change__isnull=True)._raw_delete("default")
        self.stdout.write(f"{deleted} Revisions have been deleted")
