from django.utils.translation import gettext_lazy as _
from django.db import models

from pik.core.models import Dated
from pik.core.models.base import PUided


class PIKMessageException(PUided, Dated):
    entity_uid = models.UUIDField(
        _('Идентификатор сущности'), blank=True, null=True)
    queue = models.CharField(_('Очередь'), max_length=255)
    message = models.BinaryField(_('Сообщение'))
    exception = models.JSONField(_('Ошибка'))
    exception_type = models.CharField('Тип ошибки', max_length=255)
    exception_message = models.CharField('Сообщение об ошибке', max_length=255)
    dependencies = models.JSONField('Зависимости', default=dict, blank=True)

    class Meta:
        verbose_name = _('Сообщение шины')
        verbose_name_plural = _('Сообщения шины')
