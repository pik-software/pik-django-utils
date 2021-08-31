import pytest
from django.db import IntegrityError

from pik.core.tests.fixtures import create_user
from ..models import MyOwned, MyNullOwned
from .factories import MyOwnedFactory, MyNullOwnedFactory


@pytest.fixture(name='owned_model', params=[
    (MyOwned, MyOwnedFactory),
])
def owned_model_fixture(request):
    return request.param


@pytest.fixture(name='null_owned_model', params=[
    (MyNullOwned, MyNullOwnedFactory),
])
def null_owned_model_fixture(request):
    return request.param


def test_owned_protocol(owned_model):
    _, factory = owned_model
    user = create_user()

    obj = factory.create(user=user)
    assert obj.user_id


def test_owned_protocol_no_user_problem(owned_model):
    _, factory = owned_model
    with pytest.raises(IntegrityError):
        factory.create(user=None)


def test_null_owned_protocol(null_owned_model):
    _, factory = null_owned_model
    user = create_user()

    obj = factory.create(user=user)
    assert obj.user_id


def test_null_owned_protocol_on_user_ok(null_owned_model):
    _, factory = null_owned_model
    obj = factory.create(user=None)
    assert obj.user is None
