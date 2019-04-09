from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords


class CustomHistoricalRecords(HistoricalRecords):
    DEFAULT_CHANGE_REASON_MAX_LENGTH = 100

    def __init__(self, *args, change_reason_max_length=None,**kwargs):
        super().__init__(*args, **kwargs)
        if change_reason_max_length:
            self.change_reason_max_length = change_reason_max_length
        else:
            self.change_reason_max_length = getattr(
                settings, 'SIMPLE_HISTORY_HISTORICAL_CHANGE_REASON_MAX_LENGTH',
                self.DEFAULT_CHANGE_REASON_MAX_LENGTH)

    def get_extra_fields(self, model, fields):
        extra_fields = super().get_extra_fields(model, fields)
        extra_fields['history_change_reason'].max_length = (
            self.change_reason_max_length)
        return extra_fields

class Historized(models.Model):
    history = CustomHistoricalRecords(inherit=True)

    class Meta:
        abstract = True
