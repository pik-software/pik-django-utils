from django.db import models
from simple_history.models import HistoricalRecords


class PikHistoricalRecords(HistoricalRecords):

    def contribute_to_class(self, cls, name):
        if getattr(cls, '_is_history_enabled', True):
            super().contribute_to_class(cls, name)


class Historized(models.Model):
    history = PikHistoricalRecords(inherit=True)

    class Meta:
        abstract = True
