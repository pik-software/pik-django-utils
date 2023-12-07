# # pylint: disable=protected-access
#
# from unittest.mock import Mock, call, patch, PropertyMock
#
# import pytest
#
# from bus_local.utils.producer import ResponseCommandInstanceHandler
# from test_bus_local.constants import TEST_EXCHANGE, TEST_SERVICE
#
#
# @pytest.fixture
# def response_handler():
#     return ResponseCommandInstanceHandler(
#         Mock(name='instance'), Mock(name='event_captor'), Mock(name='produce'),
#         TEST_SERVICE)
#
#
# class TestResponseCommandInstanceHandlerProduce:
#     @patch.object(
#         ResponseCommandInstanceHandler, '_exchange',
#         new_callable=PropertyMock, return_value=TEST_EXCHANGE)
#     def test_success(self, _exchange, response_handler):
#         envelope = Mock(name='envelope')
#         response_handler._produce(envelope)
#
#         expected = [
#             call(envelope, exchange='TestEntity', routing_key='test_service')]
#         assert response_handler._producer.produce.mock_calls == expected
