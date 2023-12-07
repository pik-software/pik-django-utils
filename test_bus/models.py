from django.db import models
from model_utils import Choices

from pik.core.models import BasePHistorical


class TestRequestCommand(BasePHistorical):
    requesting_service = models.CharField(max_length=255)


class TestResponseCommand(BasePHistorical):
    STATUS_CHOICES = Choices(
        ('accepted', 'принято'),
        ('processing', 'обработка'),
        ('completed', 'выполнено'),
        ('failed', 'провал'))

    request = models.ForeignKey(
        to=TestRequestCommand, on_delete=models.CASCADE)
    status = models.CharField(choices=STATUS_CHOICES, max_length=255)
    error = models.CharField(max_length=255)
