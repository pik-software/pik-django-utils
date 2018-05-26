from django.db import models
from simple_history.models import HistoricalRecords


class Historized(models.Model):
    history = HistoricalRecords(inherit=True)

    class Meta:
        abstract = True
