# pylint: disable=protected-access

from unittest.mock import Mock, call, patch, PropertyMock

from django.test import override_settings
import pytest

from pik.bus.producer import CommandEntityInstanceHandler
from test_bus.constants import TEST_SERVICE, TEST_RABBITMQ_PRODUCES
from test_bus.factories import MyTestEntityFactory, MyTestRequestCommandFactory


@pytest.mark.django_db
class TestCommandEntityInstanceHandlerProduce:
    @override_settings(RABBITMQ_PRODUCES=TEST_RABBITMQ_PRODUCES)
    @patch.object(
        CommandEntityInstanceHandler, 'host', new_callable=PropertyMock,
        return_value={})
    @patch.object(
        CommandEntityInstanceHandler, 'headers', new_callable=PropertyMock,
        return_value={})
    def test_success(self, _host, _headers):
        entity = MyTestEntityFactory()
        request = MyTestRequestCommandFactory()
        handler = CommandEntityInstanceHandler(
            entity, Mock(name='event_captor'), Mock(name='produce'),
            TEST_SERVICE, request)
        handler._models_dispatch_cache = {}  # To restore cache.
        handler._produce = Mock(wraps=handler._produce)

        handler.handle()

        expected_envelope = {
            'messageType': ['urn:message:PIK.MDM.Messages:MyTestEntity'],
            'message': {
                'guid': entity.uid,
                'type': 'MyTestEntity'},
            'host': {},
            'headers': {
                'requestGuid': str(request.uid),
                'requestType': 'mytestrequestcommand'}}
        expected = [call(
            expected_envelope,
            exchange='TestEntity.routed',
            routing_key='test_service')]
        assert handler._producer.produce.mock_calls == expected
