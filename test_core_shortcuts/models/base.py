from django.db import models

from pik.core.models import BasePHistorical


class TestNameModel(BasePHistorical):
    name = models.CharField(max_length=255)


class MySimpleModel(BasePHistorical):
    data = models.CharField(max_length=255)
    names = models.ManyToManyField(TestNameModel, blank=True)
