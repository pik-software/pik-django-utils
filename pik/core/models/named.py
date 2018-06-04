from django.db import models
from django.utils.translation import ugettext as _


class Named(models.Model):
    name = models.CharField(verbose_name=_("название"), max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        abstract = True
