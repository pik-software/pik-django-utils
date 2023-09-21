from django.core.management.base import BaseCommand

from ...tasks import clear_history


class Command(BaseCommand):
    help = 'Delete oldest rows from history models'

    def handle(self, *args, **options):
        clear_history()
