from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError


class NonChangeableValidator:
    error_msg = _('Редактирование этого поля не разрешено.')

    def __init__(self):
        self.serializer_field = None

    def set_context(self, serializer_field):
        self.serializer_field = serializer_field

    def __call__(self, value):
        instance = self.serializer_field.parent.instance

        if instance:
            old_value = getattr(instance, self.serializer_field.source)

            if old_value != value:
                raise ValidationError(self.error_msg)
