import datetime

import pytest
from freezegun import freeze_time

from ..models import MyDated
from .factories import MyDatedFactory


@pytest.fixture(params=[
    (MyDated, MyDatedFactory),
])
def dated_model(request):
    return request.param


@freeze_time("2012-01-14 03:21:34")
def test_dated_protocol(dated_model):
    model, factory = dated_model

    obj = factory.create()
    assert obj.created == datetime.datetime(2012, 1, 14, 3, 21, 34)
    assert obj.updated == datetime.datetime(2012, 1, 14, 3, 21, 34)

    with freeze_time("2012-01-14 03:21:55"):
        obj.save()
    assert obj.created == datetime.datetime(2012, 1, 14, 3, 21, 34)
    assert obj.updated == datetime.datetime(2012, 1, 14, 3, 21, 55)
