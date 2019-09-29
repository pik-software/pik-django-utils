from unittest.mock import patch

import pytest
from django.db.models import Q
from django.test import TestCase
from django.utils.crypto import get_random_string

from pik.core.shortcuts import (
    get_object_or_none, validate_and_create_object, validate_and_update_object,
    update_or_create_object)
from .factories import MySimpleModelFactory, TestNameModelFactory
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
    assert obj is not None


def test_get_object_or_none_queryset(test_model):
    model, factory = test_model
    objs = factory.create_batch(10)

    obj = get_object_or_none(model.objects.filter(data=get_random_string()))
    assert obj is None

    obj = get_object_or_none(model.objects.filter(data=objs[-1].data))
    assert obj is not None


def test_get_object_or_none_manager(test_model):
    model, factory = test_model
    objs = factory.create_batch(10)

    obj = get_object_or_none(model.objects, data=get_random_string())
    assert obj is None

    obj = get_object_or_none(model.objects, data=objs[-1].data)
    assert obj is not None


def test_get_object_or_none_args(test_model):
    model, factory = test_model
    objs = factory.create_batch(10)

    obj = get_object_or_none(model, Q(data=get_random_string()))
    assert obj is None

    obj = get_object_or_none(model, Q(data=objs[-1].data))
    assert obj is not None


def test_validate_and_create_object(test_model):
    name1 = TestNameModelFactory.create()
    name2 = TestNameModelFactory.create()
    model, factory = test_model

    kwargs = {'data': get_random_string(), 'names': [name1, name2]}
    obj = validate_and_create_object(model, **kwargs)
    assert obj.pk
    assert name1 in obj.names.all()
    assert name2 in obj.names.all()


def test_validate_and_update_object__update(test_model):
    model, factory = test_model
    name1 = TestNameModelFactory.create()
    name2 = TestNameModelFactory.create()

    obj = factory.create()
    new_data = get_random_string()
    kwargs = {'data': new_data, 'names': [name1, name2]}

    res_obj, is_updated = validate_and_update_object(obj, **kwargs)
    assert res_obj.pk == obj.pk
    assert is_updated
    assert res_obj.data == new_data
    assert name1 in res_obj.names.all()
    assert name2 in res_obj.names.all()


def test_validate_and_update_object__no_update(test_model):
    model, factory = test_model
    name1 = TestNameModelFactory.create()
    name2 = TestNameModelFactory.create()

    obj = factory.create(names=(name1, name2))
    kwargs = {'data': obj.data, 'names': [name1, name2]}

    res_obj, is_updated = validate_and_update_object(obj, **kwargs)
    assert res_obj.pk == obj.pk
    assert not is_updated
    assert res_obj.data == obj.data
    assert name1 in res_obj.names.all()
    assert name2 in res_obj.names.all()


def test_update_or_create_object__create_without_search(test_model):
    model, _ = test_model
    new_data = get_random_string()
    name1 = TestNameModelFactory.create()
    name2 = TestNameModelFactory.create()
    kwargs = {'data':new_data, 'names': [name1, name2]}

    res_obj, is_updated, is_created = update_or_create_object(
        model, **kwargs)
    assert res_obj.pk
    assert not is_updated
    assert is_created
    assert name1 in res_obj.names.all()
    assert name2 in res_obj.names.all()


def test_update_or_create_object__create(test_model):
    model, factory = test_model
    obj = factory.create()
    new_data = get_random_string()
    name1 = TestNameModelFactory.create()
    name2 = TestNameModelFactory.create()
    kwargs = {'data':new_data, 'names': [name1, name2]}

    res_obj, is_updated, is_created = update_or_create_object(
        model, search_keys=dict(data=new_data), **kwargs)
    assert res_obj.pk != obj.pk
    assert not is_updated
    assert is_created
    assert name1 in res_obj.names.all()
    assert name2 in res_obj.names.all()


def test_update_or_create_object__no_update(test_model):
    model, factory = test_model
    name1 = TestNameModelFactory.create()
    name2 = TestNameModelFactory.create()

    obj = factory.create(names=(name1, name2))
    kwargs = {'data': obj.data, 'names': [name1, name2]}

    res_obj, is_updated, is_created = update_or_create_object(
        model, search_keys=dict(data=obj.data), **kwargs)
    assert res_obj.pk == obj.pk
    assert not is_updated
    assert not is_created
    assert name1 in res_obj.names.all()
    assert name2 in res_obj.names.all()


class TestNotCallM2MUpdate(TestCase):
    @staticmethod
    @patch('pik.core.shortcuts.model_objects._update_m2m_fields')
    def test_update_or_create_object(_update_m2m_fields):
        model, factory = MySimpleModel, MySimpleModelFactory
        obj = factory.create()
        new_data = get_random_string()

        res_obj, is_updated, is_created = update_or_create_object(
            model, search_keys=dict(data=new_data), data=new_data)
        assert res_obj.pk != obj.pk
        assert not is_updated
        assert is_created
        _update_m2m_fields.assert_not_called()
