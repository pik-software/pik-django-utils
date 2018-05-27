import logging
from typing import Optional, Type, Tuple

from django.core.exceptions import ValidationError
from django.db import models, IntegrityError

LOGGER = logging.getLogger(__name__)


def get_object_or_none(model: Type[models.Model], **search_keys) \
        -> Optional[models.Model]:
    assert issubclass(model, models.Model)
    try:
        obj = model.objects.get(**search_keys)
    except model.DoesNotExist:
        obj = None
    return obj


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
        -> Tuple[models.Model, bool]:
    """
    :raises ValueError
    :return obj, is_updated
    """
    assert isinstance(obj, models.Model)
    model = type(obj)

    is_updated = False
    for key, value in kwargs.items():
        old_value = getattr(obj, key)
        if old_value == value:
            continue
        setattr(obj, key, value)
        is_updated = True

    if is_updated:
        try:
            obj.full_clean()
            obj.save()
        except (ValidationError, IntegrityError) as exc:
            LOGGER.warning(
                'Update %s error: %r (kwargs=%r)', model.__name__, exc, kwargs)
            raise ValueError(str(exc))
    return obj, is_updated


def update_or_create_object(
        model: Type[models.Model],
        search_keys: Optional[dict] = None,
        **kwargs) \
        -> Tuple[models.Model, bool, bool]:
    """
    :raises ValueError
    :return obj, is_updated, is_created
    """
    obj = get_object_or_none(model, **search_keys) if search_keys else None
    if obj:
        is_created = False
        obj, is_updated = validate_and_update_object(obj, **kwargs)
    else:
        is_updated = False
        is_created = True
        obj = validate_and_create_object(model, **kwargs)
    return obj, is_updated, is_created
