from django.db import models
from simple_history.models import HistoricalRecords


class PikHistoricalRecords(HistoricalRecords):
    def finalize(self, sender, **kwargs):
        if getattr(sender, '_is_history_enabled', True):
            super().finalize(sender, **kwargs)


class Historized(models.Model):
    history = PikHistoricalRecords(inherit=True)

    class Meta:
        abstract = True
