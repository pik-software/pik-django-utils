from django.db import models

from pik.core.models import BasePHistorical


class MySimpleModel(BasePHistorical):
    data = models.CharField(max_length=255)
