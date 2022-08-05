from pprint import pformat
from unittest.mock import patch, Mock, call
from django.test import override_settings

from pik.bus.producer import (
    producer, MDMTransaction, InstanceHandler, MessageProducer)


def test_transaction_manager():
    assert producer._transaction_messages is None  # noqa: protect-access

    with MDMTransaction():
        assert producer._transaction_messages == []  # noqa: protect-access


def test_transaction_decorator():
    assert producer._transaction_messages is None  # noqa: protect-access

    @MDMTransaction()
    def method():
        assert producer._transaction_messages == []  # noqa: protect-access
    method()
    assert producer._transaction_messages is None  # noqa: protect-access


@patch("pik.bus.producer.uuid.uuid4", Mock(return_value='0ABC..'))
@patch("pik.bus.producer.MessageProducer._publish", Mock())
def test_transaction_publish():
    with MDMTransaction():
        producer.produce(None, {})
    assert  producer._publish.call_args_list == [  # noqa: protect-access
        call(None, {'headers': {
            'transactionGUID': '0ABC..', 'transactionMessageCount': 1}})]


@override_settings(RABBITMQ_PRODUCES={
    'test_exchange': 'rest_framework.serializers.Serializer'})
@patch('pik.bus.producer.InstanceHandler._model_info_cache', {})
def test_instance_handler_models_info():
    serializer = Mock(Meta=Mock(model=Mock(__name__='test_model')))
    # to restore cache
    with patch('rest_framework.serializers.Serializer', serializer):
        assert InstanceHandler(None, None).models_info == {'test_model': {
            'exchange': 'test_exchange', 'serializer': serializer}}


@patch('pik.bus.producer.InstanceHandler._envelope', property(Mock(
    side_effect=ZeroDivisionError)))
@patch('pik.bus.producer.InstanceHandler._capture_event', Mock())
@patch('pik.bus.producer.InstanceHandler._model_info_cache', {'Mock': {}})
@patch('pik.bus.producer.MessageProducer.produce', Mock())
def test_serialization_event_failed():
    InstanceHandler(Mock(), 'test_exchange').handle()
    assert str(InstanceHandler._capture_event.call_args_list) == str([  # noqa: protect-access
        call(success=False, error=ZeroDivisionError())])


@patch('pik.bus.producer.InstanceHandler._envelope', property(
    Mock(return_value={})))
@patch('pik.bus.producer.MessageProducer._publish', Mock())
@patch('pik.bus.producer.InstanceHandler._capture_event', Mock())
@patch('pik.bus.producer.InstanceHandler._exchange', Mock())
@patch('pik.bus.producer.InstanceHandler._model_info_cache', {'Mock': {}})
def test_serialization_event_ok():
    InstanceHandler(Mock(), 'test_exchange').handle()
    assert InstanceHandler._capture_event.call_args_list == [  # noqa: protect-access
        call(success=True, error=None)]


@patch('pik.bus.producer.MessageProducer._publish', property(
    Mock(side_effect=ZeroDivisionError)))
@patch('pik.bus.producer.MessageProducer._capture_event', Mock())
def test_publication_event_fail():
    producer.produce(None, None)
    assert pformat(MessageProducer._capture_event.call_args_list) == pformat(  # noqa: protect-access
        [call(None, success=False, error=ZeroDivisionError())])


@patch('pik.bus.producer.MessageProducer._publish', Mock())
@patch('pik.bus.producer.MessageProducer._capture_event', Mock())
def test_publication_event_ok():
    producer.produce(None, None)
    assert pformat(MessageProducer._capture_event.call_args_list) == pformat([  # noqa: protect-access
        call(None, success=True, error=None)])


@patch('pik.bus.producer.uuid.uuid4', Mock(return_value='0ABC..'))
@patch('pik.bus.producer.MessageProducer._publish', Mock())
@patch('pik.bus.producer.MessageProducer._capture_event', Mock())
def test_transaction_publication_event_ok():
    with MDMTransaction():
        producer.produce(None, {'message': 1})
        producer.produce(None, {'message': 2})
        assert MessageProducer._capture_event.call_args_list == []  # noqa: protect-access
    expected = [
        call({'headers': {
            'transactionGUID': '0ABC..', 'transactionMessageCount': 2},
            'message': 1}, success=True, error=None),
        call({'headers': {
            'transactionGUID': '0ABC..', 'transactionMessageCount': 2},
            'message': 2}, success=True, error=None)]
    assert MessageProducer._capture_event.call_args_list == expected  # noqa: protect-access


@patch('pik.bus.producer.uuid.uuid4', Mock(return_value='0ABC..'))
@patch(
    'pik.bus.producer.MessageProducer._publish',
    Mock(side_effect=ZeroDivisionError))
@patch('pik.bus.producer.MessageProducer._capture_event', Mock())
def test_transaction_publication_event_fail():
    with MDMTransaction():
        producer.produce(None, {'message': 1})
        producer.produce(None, {'message': 2})
        assert MessageProducer._capture_event.call_args_list == []  # noqa: protect-access
    expected = pformat([
        call({'message': 1, 'headers': {
            'transactionGUID': '0ABC..', 'transactionMessageCount': 2}},
            success=False, error=ZeroDivisionError()),
        call({'message': 2, 'headers': {
            'transactionGUID': '0ABC..', 'transactionMessageCount': 2}},
            success=False, error=ZeroDivisionError())])
    assert pformat(MessageProducer._capture_event.call_args_list) == expected    # noqa: protect-access
