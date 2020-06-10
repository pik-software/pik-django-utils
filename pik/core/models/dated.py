from django.db import models
from django.utils.translation import gettext_lazy as _


class Dated(models.Model):
    created = models.DateTimeField(
        editable=False, auto_now_add=True, db_index=True,
        verbose_name=_('created')
    )
    updated = models.DateTimeField(
        editable=False, auto_now=True, db_index=True,
        verbose_name=_('updated')
    )

    class Meta:
        abstract = True
