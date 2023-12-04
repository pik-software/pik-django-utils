from pprint import pformat
from unittest.mock import patch, Mock, call

import pytest
from django.test import override_settings
from pika.exceptions import AMQPConnectionError

from pik.bus.producer import (
    message_producer, MDMTransaction, InstanceHandler, MessageProducer,
    MDMTransactionIsAlreadyStartedError)


def test_transaction_manager():
    assert message_producer._transaction_messages is None  # noqa: protect-access

    with MDMTransaction():
        assert message_producer._transaction_messages == []  # noqa: protect-access


def test_transaction_decorator():
    assert message_producer._transaction_messages is None  # noqa: protect-access

    @MDMTransaction()
    def method():
        assert message_producer._transaction_messages == []  # noqa: protect-access
    method()
    assert message_producer._transaction_messages is None  # noqa: protect-access


@patch("pik.bus.producer.uuid.uuid4", Mock(return_value='0ABC..'))
@patch("pik.bus.producer.MessageProducer._publish", Mock())
def test_transaction_publish_single():
    with MDMTransaction():
        message_producer.produce({}, 'exchange')
    assert message_producer._publish.call_args_list == [  # noqa: protect-access
        call({}, 'exchange', '')]


@patch("pik.bus.producer.uuid.uuid4", Mock(return_value='0ABC..'))
@patch("pik.bus.producer.MessageProducer._publish", Mock())
def test_transaction_publish_multiple():
    with MDMTransaction():
        message_producer.produce({}, 'exchange')
        message_producer.produce({}, 'exchange')
    assert message_producer._publish.call_args_list == [  # noqa: protect-access
        call({'headers': {
            'transactionGUID': '0ABC..', 'transactionMessageCount': 2}},
            'exchange', ''),
        call({'headers': {
            'transactionGUID': '0ABC..', 'transactionMessageCount': 2}},
            'exchange', '')]


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
@patch('pik.bus.producer.InstanceHandler._model_info_cache', {
    'InstanceHandler': {'Mock': {}}})
@patch('pik.bus.producer.MessageProducer.produce', Mock())
def test_serialization_event_failed():
    handler = InstanceHandler(
        Mock(name='instance'), Mock(name='event_captor'),
        Mock(name='producer'))
    handler.handle()
    assert str(InstanceHandler._capture_event.call_args_list) == str([  # noqa: protect-access
        call(success=False, error=ZeroDivisionError())])


@patch('pik.bus.producer.InstanceHandler._envelope', property(
    Mock(return_value={})))
@patch('pik.bus.producer.MessageProducer._publish', Mock())
@patch('pik.bus.producer.InstanceHandler._capture_event', Mock())
@patch('pik.bus.producer.InstanceHandler._exchange', Mock())
@patch('pik.bus.producer.InstanceHandler._model_info_cache', {
    'InstanceHandler': {'Mock': {}}})
def test_serialization_event_ok():
    handler = InstanceHandler(
        Mock(name='instance'), Mock(name='event_captor'),
        Mock(name='producer'))
    handler.handle()
    assert InstanceHandler._capture_event.call_args_list == [  # noqa: protect-access
        call(success=True, error=None)]


@patch('pik.bus.producer.MessageProducer._publish', property(
    Mock(side_effect=ZeroDivisionError)))
@patch('pik.bus.producer.MessageProducer._capture_event', Mock())
def test_publication_event_fail():
    with pytest.raises(ZeroDivisionError):
        message_producer.produce(None, None)
    assert pformat(MessageProducer._capture_event.call_args_list) == pformat(  # noqa: protect-access
        [call(None, success=False, error=ZeroDivisionError())])


@patch('pik.bus.producer.MessageProducer._produce.retry.after', Mock())
@patch('pik.bus.producer.MessageProducer._produce.retry.wait', 0)
@patch('pik.bus.producer.MessageProducer._publish', property(
    Mock(side_effect=AMQPConnectionError)))
@patch('pik.bus.producer.MessageProducer._capture_event', Mock())
def test_publication_event_fail_retry():
    with pytest.raises(AMQPConnectionError):
        message_producer.produce(None, None)
    assert pformat(MessageProducer._capture_event.call_args_list) == pformat(  # noqa: protect-access
        [call(None, success=False, error=AMQPConnectionError())] * 32)


@patch('pik.bus.producer.MessageProducer._publish', Mock())
@patch('pik.bus.producer.MessageProducer._capture_event', Mock())
def test_publication_event_ok():
    message_producer.produce(None, None)
    assert pformat(MessageProducer._capture_event.call_args_list) == pformat([  # noqa: protect-access
        call(None, success=True, error=None)])


@patch('pik.bus.producer.uuid.uuid4', Mock(return_value='0ABC..'))
@patch('pik.bus.producer.MessageProducer._publish', Mock())
@patch('pik.bus.producer.MessageProducer._capture_event', Mock())
def test_transaction_publication_event_ok():
    with MDMTransaction():
        message_producer.produce({'message': 1}, 'exchange')
        message_producer.produce({'message': 2}, 'exchange')
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
            message_producer.produce({'message': 1}, 'exchange')
            message_producer.produce({'message': 2}, 'exchange')
            assert message_producer._capture_event.call_args_list == []  # noqa: protect-access
    assert message_producer._transaction_messages is None  # noqa: protected-access
    expected = pformat([
        call({'message': 1, 'headers': {
            'transactionGUID': '0ABC..', 'transactionMessageCount': 2}},
            success=False, error=ZeroDivisionError())])
    assert pformat(message_producer._capture_event.call_args_list) == expected    # noqa: protect-access


def test_nested_transaction_fail():
    with MDMTransaction():
        with pytest.raises(MDMTransactionIsAlreadyStartedError):
            with MDMTransaction():
                message_producer.produce(None, {'message': 1})
                message_producer.produce(None, {'message': 2})


@patch('pik.bus.producer.uuid.uuid4', Mock(return_value='0ABC..'))
@patch('pik.bus.producer.MessageProducer._publish', Mock())
@patch('pik.bus.producer.MessageProducer._capture_event', Mock())
def test_single_transaction_event():
    with MDMTransaction():
        message_producer.produce({'message': 1}, 'exchange')
    assert message_producer._publish.call_args_list == [  # noqa: protected-access
        call({'message': 1}, 'exchange', '')]
    assert message_producer._capture_event.call_args_list == [call(  # noqa: protected-access
        {'message': 1}, success=True, error=None)]
