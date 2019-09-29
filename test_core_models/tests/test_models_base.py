import pytest

from .factories import MyBasePHistoricalFactory, MyBaseHistoricalFactory
from ..models import MyBasePHistorical, MyBaseHistorical


@pytest.fixture(params=[
    (MyBasePHistorical, MyBasePHistoricalFactory),
    (MyBaseHistorical, MyBaseHistoricalFactory),
])
def historical_model(request):
    return request.param


def test_historical_protocol(historical_model):
    model, factory = historical_model

    obj1 = factory.create()
    obj2 = factory.create()
    obj_last = model.objects.last()
    obj_first = model.objects.first()
    assert obj_first.pk == obj1.pk
    assert obj_last.pk == obj2.pk
    assert obj_first.created < obj_last.created
    assert obj_first.updated < obj_last.updated
    assert obj_first.version == obj_last.version
    assert obj_first.uid != obj_last.uid


def test_historical_protocol_fields(historical_model):
    model, _ = historical_model
    fields = [f.name for f in model._meta.get_fields()]  # noqa: pylint=protected-access
    assert hasattr(model, 'history')
    assert 'uid' in fields
    assert 'version' in fields
    assert 'created' in fields
    assert 'updated' in fields


def test_historical_protocol_update(historical_model):
    _, factory = historical_model
    obj = factory.create()
    version1 = obj.version
    updated1 = obj.updated
    created1 = obj.created
    obj.save()
    version2 = obj.version
    updated2 = obj.updated
    created2 = obj.created
    obj.save()
    version3 = obj.version
    updated3 = obj.updated
    created3 = obj.created
    assert version1 < version2 < version3
    assert updated1 < updated2 < updated3
    assert created1 == created2 == created3


def test_historical_protocol_history(historical_model, settings):
    settings.SOFT_DELETE_SAFE_MODE = False
    model, factory = historical_model
    obj1 = factory.create()
    obj2 = factory.create()
    obj3 = factory.create()
    uid1, uid2, uid3 = obj1.uid, obj2.uid, obj3.uid

    obj1.save()
    obj2.save()
    obj3.save()

    obj3.delete()
    obj2.delete()
    obj1.delete()

    hist2 = [(x.uid, x.history_type, x.version) for x in model.history.all()]
    assert hist2 == [
        (uid1, '-', 2), (uid2, '-', 2), (uid3, '-', 2),
        (uid3, '~', 2), (uid2, '~', 2), (uid1, '~', 2),
        (uid3, '+', 1), (uid2, '+', 1), (uid1, '+', 1),
    ]
