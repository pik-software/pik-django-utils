from django.db import models

from pik.utils.normalization import get_ordering_number


class NumericalOrderingField(models.CharField):
    def __init__(self, for_field, **kwargs):
        self.for_field = for_field
        kwargs.setdefault('db_index', True)
        kwargs.setdefault('editable', False)
        kwargs.setdefault('max_length', 255)
        super(NumericalOrderingField, self).__init__(**kwargs)

    def pre_save(self, model_instance, add):
        return get_ordering_number(getattr(model_instance, self.for_field))
