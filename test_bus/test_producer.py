from pprint import pformat
from unittest.mock import patch, Mock, call

import pytest
from django.test import override_settings
from pika.exceptions import AMQPConnectionError

from pik.bus.producer import (
    producer, MDMTransaction, InstanceHandler, MessageProducer,
    MDMTransactionIsAlreadyStarted)


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
def test_transaction_publish_single():
    with MDMTransaction():
        producer.produce({}, 'exchange')
    assert  producer._publish.call_args_list == [  # noqa: protect-access
        call({}, 'exchange', '')]


@patch("pik.bus.producer.uuid.uuid4", Mock(return_value='0ABC..'))
@patch("pik.bus.producer.MessageProducer._publish", Mock())
def test_transaction_publish_multiple():
    with MDMTransaction():
        producer.produce({}, 'exchange')
        producer.produce({}, 'exchange')
    assert  producer._publish.call_args_list == [  # noqa: protect-access
        call({'headers': {
            'transactionGUID': '0ABC..', 'transactionMessageCount': 2}}, 'exchange', ''),
        call({'headers': {
            'transactionGUID': '0ABC..', 'transactionMessageCount': 2}}, 'exchange', '')]


@override_settings(RABBITMQ_PRODUCES={
    'test_exchange': 'rest_framework.serializers.Serializer'})
@patch('pik.bus.producer.InstanceHandler._model_info_cache', {})
def test_instance_handler_models_info():
    serializer = Mock(Meta=Mock(model=Mock(__name__='test_model')))
    # to restore cache
    expected = {'test_model': {
        'exchange': 'test_exchange', 'serializer': serializer}}
    with patch('rest_framework.serializers.Serializer', serializer):
        assert InstanceHandler(None, None, None).models_info == expected


@patch('pik.bus.producer.InstanceHandler._envelope', property(Mock(
    side_effect=ZeroDivisionError)))
@patch('pik.bus.producer.InstanceHandler._capture_event', Mock())
@patch('pik.bus.producer.InstanceHandler._model_info_cache', {'Mock': {}})
@patch('pik.bus.producer.MessageProducer.produce', Mock())
def test_serialization_event_failed():
    InstanceHandler(Mock(), 'test_exchange', None).handle()
    assert str(InstanceHandler._capture_event.call_args_list) == str([  # noqa: protect-access
        call(success=False, error=ZeroDivisionError())])


@patch('pik.bus.producer.InstanceHandler._envelope', property(
    Mock(return_value={})))
@patch('pik.bus.producer.MessageProducer._publish', Mock())
@patch('pik.bus.producer.InstanceHandler._capture_event', Mock())
@patch('pik.bus.producer.InstanceHandler._exchange', Mock())
@patch('pik.bus.producer.InstanceHandler._model_info_cache', {'Mock': {}})
def test_serialization_event_ok():
    InstanceHandler(Mock(), 'test_exchange', Mock()).handle()
    assert InstanceHandler._capture_event.call_args_list == [  # noqa: protect-access
        call(success=True, error=None)]


@patch('pik.bus.producer.MessageProducer._publish', property(
    Mock(side_effect=ZeroDivisionError)))
@patch('pik.bus.producer.MessageProducer._capture_event', Mock())
def test_publication_event_fail():
    with pytest.raises(ZeroDivisionError):
        producer.produce(None, None)
    assert pformat(MessageProducer._capture_event.call_args_list) == pformat(  # noqa: protect-access
        [call(None, success=False, error=ZeroDivisionError())])


@patch('pik.bus.producer.MessageProducer._produce.retry.after', Mock())
@patch('pik.bus.producer.MessageProducer._produce.retry._wait', 0)
@patch('pik.bus.producer.MessageProducer._publish', property(
    Mock(side_effect=AMQPConnectionError)))
@patch('pik.bus.producer.MessageProducer._capture_event', Mock())
def test_publication_event_fail_retry():
    with pytest.raises(AMQPConnectionError):
        producer.produce(None, None)
    assert pformat(MessageProducer._capture_event.call_args_list) == pformat(  # noqa: protect-access
        [call(None, success=False, error=AMQPConnectionError())] * 32)


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
        producer.produce({'message': 1}, 'exchange')
        producer.produce({'message': 2}, 'exchange')
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
    with pytest.raises(ZeroDivisionError):
        with MDMTransaction():
            producer.produce({'message': 1}, 'exchange')
            producer.produce({'message': 2}, 'exchange')
            assert producer._capture_event.call_args_list == []  # noqa: protect-access
    assert producer._transaction_messages is None  # noqa: protected-access
    expected = pformat([
        call({'message': 1, 'headers': {
            'transactionGUID': '0ABC..', 'transactionMessageCount': 2}},
            success=False, error=ZeroDivisionError())])
    assert pformat(producer._capture_event.call_args_list) == expected    # noqa: protect-access


def test_nested_transaction_fail():
    with MDMTransaction():
        with pytest.raises(MDMTransactionIsAlreadyStarted):
            with MDMTransaction():
                producer.produce(None, {'message': 1})
                producer.produce(None, {'message': 2})


@patch('pik.bus.producer.uuid.uuid4', Mock(return_value='0ABC..'))
@patch('pik.bus.producer.MessageProducer._publish', Mock())
@patch('pik.bus.producer.MessageProducer._capture_event', Mock())
def test_single_transaction_event():
    with MDMTransaction():
        producer.produce({'message': 1}, 'exchange')
    assert producer._publish.call_args_list == [  # noqa: protected-access
        call({'message': 1}, 'exchange', '')]
    assert producer._capture_event.call_args_list == [call(  # noqa: protected-access
        {'message': 1}, success=True, error=None)]
