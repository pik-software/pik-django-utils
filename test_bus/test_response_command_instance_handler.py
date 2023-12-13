# pylint: disable=protected-access

from unittest.mock import Mock, call, patch, PropertyMock

from django.test import override_settings

from pik.bus.producer import ResponseCommandInstanceHandler
from test_bus.constants import (
    TEST_EXCHANGE, TEST_SERVICE, TEST_RABBITMQ_RESPONSES)


class TestResponseCommandInstanceHandlerProduce:
    @patch.object(
        ResponseCommandInstanceHandler, '_exchange',
        new_callable=PropertyMock, return_value=TEST_EXCHANGE)
    def test_success(self, _exchange):
        handler = ResponseCommandInstanceHandler(
            Mock(name='instance'), Mock(name='event_captor'),
            Mock(name='produce'), TEST_SERVICE)
        envelope = Mock(name='envelope')
        handler._produce(envelope)

        expected = [
            call(envelope, exchange='TestEntity', routing_key='test_service')]
        assert handler._producer.produce.mock_calls == expected


class TestResponseCommandInstanceGetProduceSettings:
    @override_settings(RABBITMQ_RESPONSES=TEST_RABBITMQ_RESPONSES)
    def test_success(self):
        actual = ResponseCommandInstanceHandler.get_produce_settings()
        expected = {
            'MyTestResponseCommand':
                'test_bus.serializers.MyTestResponseCommandSerializer'}
        assert actual == expected
