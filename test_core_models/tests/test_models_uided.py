import pytest

from .factories import MyUidedFactory, MyPUidedFactory
from ..models import MyUided, MyPUided


@pytest.fixture(name='uided_model', params=[
    (MyUided, MyUidedFactory),
])
def uided_model_fixture(request):
    return request.param


@pytest.fixture(name='puided_model', params=[
    (MyPUided, MyPUidedFactory),
])
def puided_model_fixture(request):
    return request.param


def test_uided_protocol(uided_model):
    model, factory = uided_model
    obj = factory.create()
    assert obj.uid
    assert obj.suid == str(obj.uid)
    assert obj.pk != obj.uid
    assert obj.stype == model._meta.model_name  # noqa


def test_puided_protocol(puided_model):
    model, factory = puided_model
    obj = factory.create()
    assert obj.uid
    assert obj.suid == str(obj.uid)
    assert obj.pk == obj.uid
    assert obj.stype == model._meta.model_name  # noqa
