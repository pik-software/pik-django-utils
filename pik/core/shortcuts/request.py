from django.http import HttpRequest
from simple_history.models import HistoricalRecords


def get_current_request() -> HttpRequest:
    return getattr(HistoricalRecords.thread, 'request', None)
