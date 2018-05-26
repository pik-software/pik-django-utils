from django.db import models
from django.utils.translation import ugettext as _


class Dated(models.Model):
    created = models.DateTimeField(
        editable=False, auto_now_add=True, verbose_name=_('Created')
    )
    updated = models.DateTimeField(
        editable=False, auto_now=True, verbose_name=_('Updated')
    )

    class Meta:
        abstract = True
