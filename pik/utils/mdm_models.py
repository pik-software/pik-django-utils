import inspect
import re
from typing import Type, Tuple, Optional, Union

from pik.api.filters import StandardizedFilterSet
from pik.api.lazy_field import LazyField
from pik.api.serializers import StandardizedModelSerializer
from pik.api.viewsets import StandardizedGenericViewSet


def _process_mixins_meta(mixin_meta: Type,
                         mixin_classes: Tuple, attrs: dict) -> Type:
    for mixin_class in mixin_classes[::-1]:
        if getattr(mixin_class, 'Meta', None):
            mixin_meta = type('Meta', (mixin_class.Meta, mixin_meta,), attrs)
    return mixin_meta


def _process_lazy_fields(new_serializer):
    """Process all serializer LazyFields and replace its path attributes
    from BaseSerializers to specific ones"""

    for _, field in (
            new_serializer._declared_fields.items()): # noqa: protected-access
        if not isinstance(field, LazyField):
            continue
        field._kwargs['path'] = (  # noqa: protected-access
            field._kwargs['path']  # noqa: protected-access
            .partition('Base')[-1])
    return new_serializer


def define_model(  # noqa: dangerous-default-value
    base_model: Type,
    mixin_classes: Union[Type, Tuple[Type], tuple] = (),
    variables=None,
    name: Optional[str] = None,
    excluded_fields=(),
) -> None:  # https://github.com/python/mypy/issues/8401
    """Define Django model dynamically"""

    if variables is None:
        variables = {}

    attrs = {'__module__': variables['__name__']}
    mixin_classes = (mixin_classes
                     if isinstance(mixin_classes, tuple)
                     else (mixin_classes,))
    meta = type('Meta', (base_model.Meta,), attrs)
    meta = _process_mixins_meta(meta, mixin_classes, attrs)
    excluded_fields = {field: None for field in excluded_fields}
    name = base_model.__name__.partition('Base')[-1] if not name else name

    new_model = type(
        name, (*mixin_classes, base_model,),
        {**attrs, **excluded_fields, 'Meta': meta})
    variables[name] = new_model


def define_serializer(  # noqa: dangerous-default-value
    base_serializer: Type,
    mixin_classes: Union[Type, Tuple[Type], tuple] = (),
    model: Optional[Type] = None,
    variables=None,
    name: Optional[str] = None,
    excluded_fields=(),
) -> None:  # https://github.com/python/mypy/issues/8401
    """Define DRF serializer dynamically"""

    if not variables:
        variables = {}

    new_serializer_name = (
        base_serializer.__name__.partition('Base')[-1]
        if not name else f'{name}Serializer')
    attrs = {'__module__': variables['__name__']}
    mixin_classes = (mixin_classes
                     if isinstance(mixin_classes, tuple)
                     else (mixin_classes,))
    meta = type('Meta', (base_serializer.Meta,), {'model': model})
    meta = _process_mixins_meta(meta, mixin_classes, attrs)
    excluded_fields = {field: None for field in excluded_fields}
    new_serializer = type(new_serializer_name,
                          (*mixin_classes, base_serializer,),
                          {**attrs, **excluded_fields, 'Meta': meta})
    new_serializer = _process_lazy_fields(new_serializer)
    variables[new_serializer_name] = new_serializer


def define_filter(  # noqa: dangerous-default-value
    base_filter: Type,
    mixin_classes: Union[Type, Tuple[Type], tuple] = (),
    model: Optional[Type] = None,
    variables=None,
    name: Optional[str] = None,
    excluded_fields=(),
) -> None:  # https://github.com/python/mypy/issues/8401
    """Define DRF filter dynamically"""

    if not variables:
        variables = {}

    new_filter_name = (
        base_filter.__name__.partition('Base')[-1]
        if not name else f'{name}Filter')
    attrs = {'__module__': variables['__name__']}
    mixin_classes = (mixin_classes
                     if isinstance(mixin_classes, tuple)
                     else (mixin_classes,))
    meta = type('Meta', (base_filter.Meta,), {'model': model})
    meta = _process_mixins_meta(meta, mixin_classes, attrs)
    excluded_fields = {field: None for field in excluded_fields}
    new_filter = type(new_filter_name,
                      (*mixin_classes, base_filter,),
                      {**attrs, **excluded_fields, 'Meta': meta})
    variables[new_filter_name] = new_filter


def define_serializers(
        base_module, variables, models_module, excluded_fields=()):
    predicate = lambda x: inspect.isclass(x) and issubclass(  # noqa: lambda
        x, StandardizedModelSerializer)
    definitions = get_module_classes(base_module, predicate)
    for base_name, base in definitions.items():
        match = re.match('Base(?P<name>.+)Serializer', base_name)
        if not match or f'{match["name"]}Serializer' in variables:
            continue
        define_serializer(
            base, (), getattr(models_module, match["name"]),
            variables, excluded_fields=excluded_fields)


def define_filters(
        base_module, variables, models_module, excluded_fields=()):
    predicate = lambda x: inspect.isclass(x) and issubclass(  # noqa: lambda
        x, StandardizedFilterSet)
    definitions = get_module_classes(base_module, predicate)
    for base_name, base in definitions.items():
        match = re.match('Base(?P<name>.+)Filter', base_name)
        if not match or f'{match["name"]}Filter' in variables:
            continue
        define_filter(
            base, (), getattr(models_module, match["name"]),
            variables, excluded_fields=excluded_fields)


def define_missing_classes(base_module, variables, base_class):
    def is_model(item):
        return (
            inspect.isclass(item)
            and item.__module__ == base_module.__name__
            and issubclass(item, base_class))

    for name, base in inspect.getmembers(base_module, is_model):
        match = re.match('Base(?P<name>.+)', name)
        if not match or match['name'] in variables:
            continue

        variables[match['name']] = type(
            match['name'], (base, ), {'__module__': variables['__name__']})


def get_module_classes(module, predicate=None):
    return {
        name: item
        for name, item in inspect.getmembers(module, predicate)
        if item.__module__ == module.__name__
    }


def define_missing_viewsets(variables, base_viewsets, serializers, filters):
    predicate = lambda x: inspect.isclass(x) and issubclass(  # noqa: lambda
        x, StandardizedGenericViewSet)
    definitions = get_module_classes(base_viewsets, predicate)
    for base_name, base in definitions.items():
        match = re.match('Base(?P<name>.+)ViewSet', base_name)
        if not match:
            continue
        serializer_name = f'{match["name"]}Serializer'
        viewset_name = f'{match["name"]}ViewSet'
        filter_name = f'{match["name"]}Filter'
        if viewset_name not in variables:
            variables[viewset_name] = type(
                viewset_name, (base, ), {
                    '__module__': variables['__name__'],
                    'serializer_class': getattr(serializers, serializer_name),
                    'filterset_class': getattr(filters, filter_name)
                })
