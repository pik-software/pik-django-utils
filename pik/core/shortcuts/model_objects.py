import logging
from typing import Optional, Type, Tuple, Union, List

from django.core.exceptions import ValidationError
from django.db import models, IntegrityError

LOGGER = logging.getLogger(__name__)


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
    obj = model(**kwargs)
    try:
        obj.full_clean()
        obj.save()
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
