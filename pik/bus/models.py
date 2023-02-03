from django.contrib.postgres.indexes import GinIndex
from django.db.models import Index
from django.utils.translation import gettext_lazy as _
from django.db import models

from pik.core.models import Dated
from pik.core.models.base import PUided


class PIKMessageException(PUided, Dated):
    entity_uid = models.UUIDField(
        _('Идентификатор сущности'), blank=True, null=True)
    body_hash = models.CharField(
        _('sha1'), max_length=40, blank=True, null=True)
    queue = models.CharField(_('Очередь'), max_length=255, db_index=True)
    message = models.BinaryField(_('Сообщение'))
    exception = models.JSONField(_('Ошибка'))
    exception_type = models.CharField(
        'Тип ошибки', max_length=255, db_index=True)
    exception_message = models.CharField('Сообщение об ошибке', max_length=255)
    dependencies = models.JSONField('Зависимости', default=dict, blank=True)
    has_dependencies = models.BooleanField(
        'Имеет зависимости', default=False, db_index=True)

    class Meta:
        verbose_name = _('Сообщение шины')
        verbose_name_plural = _('Сообщения шины')
        indexes = [
            GinIndex('dependencies', name='dependencies_indx_2412'),
            Index(fields=('has_dependencies', 'queue')),
            Index(fields=('queue', )),
        ]
        unique_together = [['queue', 'entity_uid']]

    def save(self, *args, **kwargs):
        self.has_dependencies = bool(self.dependencies)
        super().save(*args, **kwargs)
