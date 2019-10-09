from django.db import models

from pik.core.models import BasePHistorical


class TestNameModel(BasePHistorical):
    name = models.CharField(max_length=255)


class MySimpleModel(BasePHistorical):
    data = models.CharField(max_length=255)
    names = models.ManyToManyField(TestNameModel, blank=True)


class MyModelManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()


class ModelWithOverriddenQueryset(BasePHistorical):
    name = models.CharField(max_length=255)

    test_objects = MyModelManager()
