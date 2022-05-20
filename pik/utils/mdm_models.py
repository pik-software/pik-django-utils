import types
from typing import List, Type, Tuple

from pik.api.lazy_field import LazyField


def _process_mixins_meta(mixin_meta: Type,
                         mixin_classes: Tuple, attrs: dict) -> Type:
    for mixin_class in mixin_classes[::-1]:
        if getattr(mixin_class, 'Meta', None):
            mixin_meta = type('Meta', (mixin_class.Meta, mixin_meta,), attrs)
    return mixin_meta


def define_models( # noqa: dangerous-default-value
    names: List[str],
    base_module: types.ModuleType,
    variables: dict,
    mixins: dict = {},
) -> None:
    """Define Django models dynamically using its names and
    module with its base models provided"""

    for name in names:
        base_model = getattr(base_module, f'Base{name}')
        attrs = {'__module__': variables['__name__']}
        mixin_classes = mixins.get(name, ())
        meta = type('Meta', (base_model.Meta,), attrs)
        meta = _process_mixins_meta(meta, mixin_classes, attrs)
        excluded_fields = {
            field: None
            for mixin in mixin_classes
            for field in getattr(mixin, 'EXCLUDE_PARENT_FIELDS', ())
        }
        new_model = type(
            name, (*mixin_classes, base_model,),
            {**attrs, **excluded_fields, 'Meta': meta})
        variables[name] = new_model


def _process_lazy_fields(new_serializer):
    """Process all serializer LazyFields and replace its path attributes
    from BaseSerializers to specific ones"""

    for _, field in \
            new_serializer._declared_fields.items(): # noqa: protected-access
        if not isinstance(field, LazyField):
            continue
        path = field._kwargs['path'] # noqa: protected-access
        if path.startswith('Base'):
            new_path = path[len('Base'):]
            field._kwargs['path'] = new_path # noqa: protected-access
    return new_serializer


def define_serializers( # noqa: dangerous-default-value
    names: List[str],
    base_module: types.ModuleType,
    variables: dict,
    model_module: types.ModuleType,
    mixins: dict = {},
) -> None:
    """Define DRF serializers dynamically using its model names
    and module with its base serializers provided"""

    for name in names:
        new_serializer_name = f'{name}Serializer'
        base_serializer = getattr(base_module, f'Base{new_serializer_name}')
        model = getattr(model_module, name)
        # Set up `Meta` class
        attrs = {'__module__': variables['__name__']}
        mixin_classes = mixins.get(name, ())
        meta = type('Meta', (base_serializer.Meta,), {'model': model})
        meta = _process_mixins_meta(meta, mixin_classes, attrs)
        new_serializer = type(new_serializer_name,
                              (*mixin_classes, base_serializer,),
                              {**attrs, 'Meta': meta})
        new_serializer = _process_lazy_fields(new_serializer)
        variables[new_serializer_name] = new_serializer
