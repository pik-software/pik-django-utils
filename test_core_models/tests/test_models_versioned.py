import pytest

from .factories import MyVersionedFactory, MyStrictVersionedFactory
from ..models import MyVersioned, MyStrictVersioned


@pytest.fixture(params=[
    (MyVersioned, MyVersionedFactory),
])
def versioned_model(request):
    return request.param


@pytest.fixture(params=[
    (MyStrictVersioned, MyStrictVersionedFactory),
])
def strict_versioned_model(request):
    return request.param


def test_versioned_protocol(versioned_model):
    model, factory = versioned_model
    obj = factory.create()
    version1 = obj.version
    assert isinstance(obj.version, int)
    assert obj.version > 0

    obj.save()
    version2 = obj.version
    assert version2 > version1


def test_strict_versioned_protocol(strict_versioned_model):
    model, factory = strict_versioned_model
    obj = factory.create()
    version1 = obj.version
    assert isinstance(obj.version, int)
    assert obj.version > 0

    obj.save()
    version2 = obj.version
    with pytest.raises(TypeError):
        assert version2 > version1

    obj.refresh_from_db()
    assert obj.version > version1


def test_optimistic_concurrency_update(versioned_model):
    model, factory = versioned_model
    obj = factory.create()
    version1 = obj.version
    is_updated = obj.optimistic_concurrency_update()
    obj.refresh_from_db()
    version2 = obj.version
    assert is_updated
    assert version1 < version2
