import pytest
from django.utils.crypto import get_random_string

from pik.core.shortcuts import get_object_or_none, validate_and_create_object, \
    validate_and_update_object, update_or_create_object
from .factories import MySimpleModelFactory
from ..models import MySimpleModel


@pytest.fixture(params=[
    (MySimpleModel, MySimpleModelFactory),
])
def test_model(request):
    return request.param


def test_get_object_or_none(test_model):
    model, factory = test_model
    objs = factory.create_batch(10)

    obj = get_object_or_none(model, data=get_random_string())
    assert obj is None

    obj = get_object_or_none(model, data=objs[-1].data)
    assert obj.pk


def test_validate_and_create_object(test_model):
    model, factory = test_model

    obj = validate_and_create_object(model, data=get_random_string())
    assert obj.pk


def test_validate_and_update_object__update(test_model):
    model, factory = test_model
    obj = factory.create()
    new_data = get_random_string()

    res_obj, is_updated = validate_and_update_object(obj, data=new_data)
    assert res_obj.pk == obj.pk
    assert is_updated
    assert res_obj.data == new_data


def test_validate_and_update_object__no_update(test_model):
    model, factory = test_model
    obj = factory.create()

    res_obj, is_updated = validate_and_update_object(obj, data=obj.data)
    assert res_obj.pk == obj.pk
    assert not is_updated
    assert res_obj.data == obj.data


def test_update_or_create_object__create_without_search(test_model):
    model, _ = test_model
    new_data = get_random_string()

    res_obj, is_updated, is_created = update_or_create_object(
        model, data=new_data)
    assert res_obj.pk
    assert not is_updated
    assert is_created


def test_update_or_create_object__create(test_model):
    model, factory = test_model
    obj = factory.create()
    new_data = get_random_string()

    res_obj, is_updated, is_created = update_or_create_object(
        model, search_keys=dict(data=new_data), data=new_data)
    assert res_obj.pk != obj.pk
    assert not is_updated
    assert is_created


def test_update_or_create_object__no_update(test_model):
    model, factory = test_model
    obj = factory.create()

    res_obj, is_updated, is_created = update_or_create_object(
        model, search_keys=dict(data=obj.data), data=obj.data)
    assert res_obj.pk == obj.pk
    assert not is_updated
    assert not is_created
