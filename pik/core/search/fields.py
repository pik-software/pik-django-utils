from django.contrib.postgres.search import SearchVectorField
from django.db.models.signals import pre_save

from .signals import update_search_index


class SearchIndexField(SearchVectorField):
    def __init__(self, search_fields, default='', editable=False, blank=True,
                 **kwargs):
        self.search_fields = search_fields
        super().__init__(
            default=default, editable=editable, blank=blank, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return (name, path, args,
                {**kwargs, 'search_fields': self.search_fields})

    def contribute_to_class(self, cls, name, private_only=False):
        super().contribute_to_class(cls, name, private_only=private_only)

        # Caching search index field names list instead of filtering
        # over _meta.get_fields during updates
        if not hasattr(cls, '_search_index_fields'):
            cls._search_index_fields = []  # noqa: protected-access
        cls._search_index_fields.append(name)  # noqa: protected-access
        pre_save.connect(update_search_index, sender=cls)
