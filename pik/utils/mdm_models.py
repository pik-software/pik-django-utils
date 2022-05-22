import types
from typing import List, Type, Tuple, Optional, Union

from pik.api.lazy_field import LazyField


def _process_mixins_meta(mixin_meta: Type,
                         mixin_classes: Tuple, attrs: dict) -> Type:
    for mixin_class in mixin_classes[::-1]:
        if getattr(mixin_class, 'Meta', None):
            mixin_meta = type('Meta', (mixin_class.Meta, mixin_meta,), attrs)
    return mixin_meta


def define_model(  # noqa: dangerous-default-value
    base_model: Type,
    mixin_classes: Union[Type, Tuple[Type]] = (),
    variables: Optional[dict] = {},
    name: Optional[str] = None,
    excluded_fields: Optional[tuple] = (),
) -> None:  # https://github.com/python/mypy/issues/8401
    """Define Django model dynamically"""

    attrs = {'__module__': variables['__name__']}
    mixin_classes = (mixin_classes
                     if isinstance(mixin_classes, tuple)
                     else (mixin_classes,))
    meta = type('Meta', (base_model.Meta,), attrs)
    meta = _process_mixins_meta(meta, mixin_classes, attrs)
    excluded_fields = {field: None for field in excluded_fields}
    name = base_model.__name__.lstrip('Base') if not name else name
    new_model = type(
        name, (*mixin_classes, base_model,),
        {**attrs, **excluded_fields, 'Meta': meta})
    variables[name] = new_model


def define_models(  # noqa: dangerous-default-value
    names: List[str],
    base_module: types.ModuleType,
    variables: dict,
    mixins: dict = {},
) -> None:  # https://github.com/python/mypy/issues/8401
    """Define Django models dynamically using its names and
    module with its base models provided"""

    for name in names:
        base_model = getattr(base_module, f'Base{name}')
        mixin_classes = mixins.get(name, ())
        excluded_fields = tuple(
            field
            for mixin in mixin_classes
            for field in getattr(mixin, 'EXCLUDE_PARENT_FIELDS', ())
        )
        define_model(base_model, mixin_classes,
                     variables, name, excluded_fields)


def _process_lazy_fields(new_serializer):
    """Process all serializer LazyFields and replace its path attributes
    from BaseSerializers to specific ones"""

    for _, field in \
            new_serializer._declared_fields.items(): # noqa: protected-access
        if not isinstance(field, LazyField):
            continue
        field._kwargs['path'] = field._kwargs['path'].lstrip('Base') # noqa:
        # protected-access
    return new_serializer


def define_serializer(  # noqa: dangerous-default-value
    base_serializer: Type,
    mixin_classes: Union[Type, Tuple[Type]] = (),
    model: Type = None,
    variables: Optional[dict] = {},
    name: Optional[str] = None,
    excluded_fields: Optional[tuple] = (),
) -> None:  # https://github.com/python/mypy/issues/8401
    """Define DRF serializer dynamically"""

    new_serializer_name = (
        base_serializer.__name__.lstrip('Base')
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


def define_serializers(  # noqa: dangerous-default-value
    names: List[str],
    base_module: types.ModuleType,
    variables: dict,
    model_module: types.ModuleType,
    mixins: dict = {},
) -> None:  # https://github.com/python/mypy/issues/8401
    """Define DRF serializers dynamically using its model names
    and module with its base serializers provided"""

    for name in names:
        new_serializer_name = f'{name}Serializer'
        base_serializer = getattr(base_module, f'Base{new_serializer_name}')
        model = getattr(model_module, name)
        mixin_classes = mixins.get(name, ())
        define_serializer(base_serializer, mixin_classes,
                          model, variables, name)
