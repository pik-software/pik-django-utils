from typing import Optional

from django.http import HttpRequest
from simple_history.models import HistoricalRecords


def get_current_request() -> Optional[HttpRequest]:
    return getattr(HistoricalRecords.thread, 'request', None)
