# pylint: disable=protected-access
import pytest

from ..models import MySoftDeleted
from ..tests.factories import MySoftDeletedFactory


@pytest.fixture(params=[
    (MySoftDeleted, MySoftDeletedFactory),
])
def model_and_factory(request):
    return request.param


def test_soft_delete_obj(model_and_factory):
    model, factory = model_and_factory
    obj = factory.create()
    obj_pk = obj.pk

    obj.delete()

    assert not model.objects.filter(pk=obj_pk).last()
    assert not model._default_manager.filter(pk=obj_pk).last()
    assert model.all_objects.filter(pk=obj_pk).last()
    assert model._base_manager.filter(pk=obj_pk).last()


def test_soft_delete_qs(model_and_factory):
    model, factory = model_and_factory
    obj = factory.create()
    obj_pk = obj.pk

    model.objects.filter(pk=obj_pk).delete()

    assert not model.objects.filter(pk=obj_pk).last()
    assert not model._default_manager.filter(pk=obj_pk).last()
    assert model.all_objects.filter(pk=obj_pk).last()
    assert model._base_manager.filter(pk=obj_pk).last()


@pytest.mark.skip
def test_hard_delete_obj(model_and_factory):
    model, factory = model_and_factory
    obj = factory.create()
    obj_pk = obj.pk

    obj.hard_delete()

    assert not model.objects.filter(pk=obj_pk).last()
    assert not model._default_manager.filter(pk=obj_pk).last()
    assert not model.all_objects.filter(pk=obj_pk).last()
    assert not model._base_manager.filter(pk=obj_pk).last()


@pytest.mark.skip
def test_hard_delete_qs(model_and_factory):
    model, factory = model_and_factory
    obj = factory.create()
    obj_pk = obj.pk

    model.objects.filter(pk=obj_pk).hard_delete()

    assert not model.objects.filter(pk=obj_pk).last()
    assert not model._default_manager.filter(pk=obj_pk).last()
    assert not model.all_objects.filter(pk=obj_pk).last()
    assert not model._base_manager.filter(pk=obj_pk).last()
