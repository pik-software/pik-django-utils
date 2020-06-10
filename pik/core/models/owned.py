from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Owned(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_('User'),
        related_name='%(class)ss', db_index=True,
        on_delete=models.CASCADE, editable=False)

    class Meta:
        abstract = True


class NullOwned(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_('User'),
        related_name='%(class)ss', db_index=True,
        on_delete=models.CASCADE, editable=False,
        null=True)

    class Meta:
        abstract = True
