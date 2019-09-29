from uuid import uuid4

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.functional import cached_property


class Uided(models.Model):
    uid = models.UUIDField(unique=True, default=uuid4, editable=False)

    @property
    def suid(self) -> str:
        return str(self.uid)

    @cached_property
    def stype(self):
        return ContentType.objects.get_for_model(type(self)).model

    def __str__(self):
        return self.suid

    class Meta:
        abstract = True


class PUided(models.Model):
    """
    Primary Uided
    """
    uid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    @property
    def suid(self) -> str:
        return str(self.uid)

    @cached_property
    def stype(self):
        return ContentType.objects.get_for_model(type(self)).model

    def __str__(self):
        return self.suid

    class Meta:
        abstract = True
