import pytest

from .factories import MyNamedFactory
from ..models import MyNamed


@pytest.fixture(params=[
    (MyNamed, MyNamedFactory),
])
def named_model(request):
    return request.param


def test_named_model(named_model):
    model, factory = named_model
    obj = factory.create(name='name')
    assert obj.name == 'name'
