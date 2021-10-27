from functools import reduce, partial

from django.contrib.postgres.search import SearchQuery
from django.db import migrations
from django.db.models.expressions import RawSQL
from django.utils.module_loading import import_string

from .constants import PG_SEARCH_RUSSIAN_LANGUAGE_CONFIG


class SearchIndexRedundantFieldsException(Exception):
    pass


def check_search_config_consistency(model, search_fields):
    """ Check search_fields through search index fields configuration

    >>> from unittest.mock import Mock

    >>> check_search_config_consistency( \
            Mock(_search_index_fields=['search_index']), [])

    >>> check_search_config_consistency(\
            Mock(_search_index_fields=[]), ['name'])

    >>> check_search_config_consistency(\
            Mock(_search_index_fields=[]), ['first_name', 'last_name'])

    >>> check_search_config_consistency( \
            Mock(_search_index_fields=['search_index']), ['search_index'])

    >>> check_search_config_consistency( \
            Mock(_search_index_fields=['search_index']), \
            ['search_index', 'name'])
    Traceback (most recent call last):
        ...
    pik.core.search.utils.SearchIndexRedundantFieldsException: \
SearchIndexField can't be used with other fields in `search_fields`! \
Multiple found: (search_index, name). To add more fields use \
`SearchIndexField.search_fields` arg!

    >>> check_search_config_consistency( \
            Mock(_search_index_fields=[ \
                'search_index', 'custom_search_index']), \
            ['search_index', 'custom_search_index'])
    Traceback (most recent call last):
        ...
    pik.core.search.utils.SearchIndexRedundantFieldsException: \
SearchIndexField can't be used with other fields in `search_fields`! \
Multiple found: (search_index, custom_search_index). To add more fields use \
`SearchIndexField.search_fields` arg!

    """

    if len(search_fields) < 2:
        return

    if not getattr(model, '_search_index_fields', []):
        return

    search_index_fields = set(model._search_index_fields) & set(search_fields)  # noqa: protected-access
    if not search_index_fields:
        return

    raise SearchIndexRedundantFieldsException(
        'SearchIndexField can\'t be used with other fields in `search_fields`!'
        f' Multiple found: ({", ".join(search_fields)}).'
        ' To add more fields use `SearchIndexField.search_fields` arg!')


def to_tsvector(value):
    return RawSQL(
        'to_tsvector(%s, %s)', (PG_SEARCH_RUSSIAN_LANGUAGE_CONFIG, value))


def get_search_index(obj, search_fields):
    """
    Generates search index string from given fields

    >>> from types import SimpleNamespace as Obj
    >>> obj = Obj(attr1='Attr1', attr2='Attr2', nested=Obj(subattr='SubAttr'))

    >>> get_search_index(obj, [])
    ''

    >>> get_search_index(obj, ['attr1'])
    'Attr1'

    >>> get_search_index(obj, ['attr1', 'attr2'])
    'Attr1 Attr2'

    >>> get_search_index(obj, ['attr1', 'nested__subattr'])
    'Attr1 SubAttr'
    """

    common_search_field = []
    for field in search_fields:
        if '__' in field:
            try:
                related_name = reduce(getattr, field.split('__'), obj)
                if related_name:
                    common_search_field.append(related_name)
            except AttributeError:
                pass
        else:
            attr = getattr(obj, field)
            if attr:
                common_search_field.append(str(attr))
    return ' '.join(common_search_field)


def filter_queryset_by_search_index(queryset, field, value):
    if value:
        lookup = {
            field: SearchQuery(
                value, config=PG_SEARCH_RUSSIAN_LANGUAGE_CONFIG)}
        return queryset.filter(**lookup)
    return queryset


def search_index_migration(app, model, *args, **kwargs):
    return migrations.RunPython(
        partial(fill_search_indexes_migration, app, model),
        partial(empty_search_indexes_migration, app, model),
        *args, **kwargs)


def fill_search_indexes_migration(app, model, apps, schema_editor):
    # Cyclic import workaround
    search_index_field = import_string('core.search.fields.SearchIndexField')

    model = apps.get_model(app, model)

    # We are unable to access model._search_index_fields, so filtering
    # through _meta.get_fields
    index_fields = [field for field in model._meta.get_fields()  # noqa protected-access
                    if isinstance(field, search_index_field)]

    # There is possible problem with searching through soft deleted items
    objects = model.objects.all()
    if hasattr(model, 'all_objects'):
        objects = model.all_objects.all()

    for instance in objects:
        for field in index_fields:
            search_index = get_search_index(instance, field.search_fields)
            setattr(instance, field.name, to_tsvector(search_index))
            instance.save()


def empty_search_indexes_migration(app, model, apps, schema_editor):
    apps.get_model(app, model).objects.update(search_index='')
