from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError


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
    error_msg = _('Новое значене поля updated должно быть больше предыдущего.')

    def __call__(self, attrs, serializer):
        old_updated = getattr(serializer.instance, 'updated', None)
        new_updated = attrs.get('updated')
        if not old_updated or not new_updated:
            return
        if new_updated < old_updated:
            raise ValidationError(self.error_msg)
