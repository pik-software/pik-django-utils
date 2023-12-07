# pylint: disable=protected-access

from unittest.mock import Mock, call, patch, PropertyMock

import pytest

from pik.bus.producer import CommandEntityInstanceHandler
from test_bus.constants import TEST_SERVICE, TEST_MDM_SERIALIZERS
from test_bus.factories import (
    TestEntityFactory, TestRequestCommandFactory)


@pytest.mark.django_db
class TestCommandEntityInstanceHandlerProduce:
    @patch.object(
        CommandEntityInstanceHandler, '_mdm_serializers',
        new_callable=PropertyMock, return_value=TEST_MDM_SERIALIZERS)
    @patch.object(
        CommandEntityInstanceHandler, 'host', new_callable=PropertyMock,
        return_value={})
    @patch.object(
        CommandEntityInstanceHandler, 'headers', new_callable=PropertyMock,
        return_value={})
    def test_success(self, _mdm_serializers, _host, _headers):
        entity = TestEntityFactory()
        request = TestRequestCommandFactory()
        handler = CommandEntityInstanceHandler(
            entity, Mock(name='event_captor'), Mock(name='produce'),
            TEST_SERVICE, request)
        # Clearing class level cache after testing with other InstanceHandler
        # children.
        handler._models_dispatch_cache = {}
        handler._produce = Mock(wraps=handler._produce)

        handler.handle()

        expected_envelope = {
            'messageType': ['urn:message:PIK.MDM.Messages:TestEntity'],
            'message': {
                'guid': entity.uid,
                'type': 'TestEntity'},
            'host': {},
            'headers': {
                'requestGuid': str(request.uid),
                'requestType': 'testrequestcommand'}}
        expected = [call(
            expected_envelope,
            exchange='TestEntity.routed',
            routing_key='test_service')]
        assert handler._producer.produce.mock_calls == expected
