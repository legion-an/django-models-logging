from datetime import datetime

from django.core.management.base import BaseCommand

from models_logging.models import Change


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            '--ctype', type=str, help='ids by comma of content_type wich will be delete'
        )
        parser.add_argument(
            '--exclude', type=str, help='ids by comma of content_type wich will not! be delete'
        )
        parser.add_argument(
            '--date_lte', type=str, help='The changes started before that date will be removed, format (yyyy.mm.dd)',
        )

    def handle(self, *args, **options):
        content_type = options['ctype']
        date_lte = options['date_lte']
        exclude = options['exclude']

        changes = Change.objects.all()
        if content_type:
            changes = changes.filter(content_type__id__in=content_type.split(','))
        if exclude:
            changes = changes.exclude(content_type__id__in=exclude.split(','))
        if date_lte:
            changes = changes.filter(date_created__lte=datetime.strptime(date_lte, '%Y.%m.%d'))

        changes.delete()