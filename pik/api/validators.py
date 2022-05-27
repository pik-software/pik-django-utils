from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError


class NonChangeableValidator:
    error_msg = _('Редактирование этого поля не разрешено.')
    requires_context = True

    def __init__(self):
        self.serializer_field = None

    def __call__(self, value, serializer_field):
        instance = serializer_field.parent.instance

        if instance:
            old_value = serializer_field.to_internal_value(
                getattr(instance, serializer_field.source))

            if old_value != value:
                raise ValidationError(self.error_msg)
