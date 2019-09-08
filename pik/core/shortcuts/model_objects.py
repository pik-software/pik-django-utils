import logging
from typing import Optional, Type, Tuple, Union, List

from django.core.exceptions import ValidationError
from django.db import models, IntegrityError

LOGGER = logging.getLogger(__name__)


def _update_m2m_fields(_obj, **kwargs):
    for key, values in kwargs.items():
        for value in values:
            m2m_set = getattr(_obj, key)
            if value not in m2m_set.all():
                m2m_set.add(value)


def _get_m2m_kwargs(_model, **kwargs):
    m2m_kwargs = {}
    for field in _model._meta.get_fields():  # noqa: pylint=protected-access
        if (field.get_internal_type() == 'ManyToManyField'
                and field.name in kwargs):
            m2m_kwargs[field.name] = kwargs.pop(field.name)
    return m2m_kwargs, kwargs


def get_object_or_none(
        source: Union[Type[models.Model], models.QuerySet, models.Manager],
        *args, **kwargs) -> Optional[models.Model]:
    assert (isinstance(source, (models.QuerySet, models.Manager))
            or issubclass(source, models.Model))

    if not isinstance(source, (models.QuerySet, models.Manager)):
        source = source.objects

    try:
        return source.get(*args, **kwargs)
    except source.model.DoesNotExist:
        return None


def validate_and_create_object(model: Type[models.Model], **kwargs) \
        -> models.Model:
    """
    :raises ValueError
    :return obj
    """
    assert issubclass(model, models.Model)

    m2m_kwargs, kwargs = _get_m2m_kwargs(model, **kwargs)

    obj = model(**kwargs)
    try:
        obj.full_clean()
        obj.save()
        if m2m_kwargs:
            _update_m2m_fields(obj, **m2m_kwargs)

    except (ValidationError, IntegrityError) as exc:
        LOGGER.warning(
            'Create %s error: %r (kwargs=%r)', model.__name__, exc, kwargs)
        raise ValueError(str(exc))
    return obj


def validate_and_update_object(obj: models.Model, **kwargs) \
        -> Tuple[models.Model, List[str]]:
    """
    :raises ValueError
    :return obj, is_updated
    """
    assert isinstance(obj, models.Model)
    model = type(obj)

    m2m_kwargs, kwargs = _get_m2m_kwargs(model, **kwargs)

    updated_keys = {}
    for key, value in kwargs.items():
        old_value = getattr(obj, key)
        if old_value == value:
            continue
        setattr(obj, key, value)
        updated_keys[key] = old_value

    if updated_keys:
        try:
            obj.full_clean()
            obj.save()
            if m2m_kwargs:
                _update_m2m_fields(obj, **m2m_kwargs)

        except (ValidationError, IntegrityError) as exc:
            for key, old_value in updated_keys.items():
                setattr(obj, key, old_value)
            LOGGER.warning(
                'Update %s error: %r (kwargs=%r)', model.__name__, exc, kwargs)
            raise ValueError(str(exc))
    return obj, list(updated_keys.keys())


def update_or_create_object(
        model: Type[models.Model],
        search_keys: Optional[dict] = None,
        **kwargs) \
        -> Tuple[models.Model, List[str], bool]:
    """
    :raises ValueError
    :return obj, is_updated, is_created
    """
    obj = get_object_or_none(model, **search_keys) if search_keys else None
    if obj:
        is_created = False
        obj, updates = validate_and_update_object(obj, **kwargs)
    else:
        updates = []
        is_created = True
        obj = validate_and_create_object(model, **kwargs)
    return obj, updates, is_created
