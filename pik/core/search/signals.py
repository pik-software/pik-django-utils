from .utils import get_search_index, to_tsvector


def update_search_index(instance, **kwargs):
    for field_name in getattr(instance, '_search_index_fields', []):
        field = instance._meta.get_field(field_name)  # noqa protected-access
        search_index = get_search_index(instance, field.search_fields)

        # Using RAW SQL `to_tsvector` function to reduce query count
        setattr(instance, field_name, to_tsvector(search_index))
