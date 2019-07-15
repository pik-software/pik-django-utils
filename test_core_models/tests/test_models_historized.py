import pytest

from .factories import MyHistorizedFactory
from ..models import MyHistorized


@pytest.fixture(params=[
    (MyHistorized, MyHistorizedFactory),
])
def historized_model(request):
    return request.param


def test_historized_protocol(historized_model, settings):
    settings.SOFT_DELETE_SAFE_MODE = False
    model, factory = historized_model
    obj = factory.create()
    history = obj.history.all()
    assert obj.history
    assert obj.history.count() == 1

    obj.save()
    assert obj.history.count() == 2

    obj.delete()
    assert obj.history.count() == 0
    assert history.count() == 3

    hist_obj1 = history.last()
    hist_obj2 = history[1]
    hist_obj3 = history.first()
    assert isinstance(hist_obj3.history_id, int)
    assert hist_obj3.pk == hist_obj3.history_id
    assert hist_obj3.history_change_reason is None
    assert hist_obj3.history_id > hist_obj1.history_id

    assert hist_obj1.history_type == '+'
    assert hist_obj2.history_type == '~'
    assert hist_obj3.history_type == '-'
