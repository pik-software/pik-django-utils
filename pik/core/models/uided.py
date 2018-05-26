import ulid
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.functional import cached_property


def _new_uid():
    return ulid.new().uuid


class Uided(models.Model):
    uid = models.UUIDField(unique=True, default=_new_uid, editable=False)

    @property
    def suid(self) -> str:
        return str(self.uid)

    @cached_property
    def stype(self):
        return ContentType.objects.get_for_model(type(self)).model

    def __str__(self):
        return self.suid

    class Meta:
        ordering = ['-uid']
        abstract = True


class PUided(models.Model):
    """
    Primary Uided
    """
    uid = models.UUIDField(primary_key=True, default=_new_uid, editable=False)

    @property
    def suid(self) -> str:
        return str(self.uid)

    @cached_property
    def stype(self):
        return ContentType.objects.get_for_model(type(self)).model

    def __str__(self):
        return self.suid

    class Meta:
        ordering = ['-uid']
        abstract = True
