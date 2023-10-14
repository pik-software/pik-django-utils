from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from pik.api.exceptions import NewestUpdateValidationError


class NonChangeableValidator:
    requires_context = True
    error_msg = _('Редактирование этого поля не разрешено.')

    def __init__(self):
        self.serializer_field = None

    def __call__(self, value, serializer_field):
        instance = serializer_field.parent.instance

        if instance:
            old_value = serializer_field.to_internal_value(
                getattr(instance, serializer_field.source))

            if old_value != value:
                raise ValidationError(self.error_msg)


class NewestUpdateValidator:
    requires_context = True

    def __call__(self, value, serializer_field):
        updated = getattr(serializer_field.parent.instance, 'updated', None)
        if not updated:
            return
        if value >= updated:
            return
        raise NewestUpdateValidationError()
