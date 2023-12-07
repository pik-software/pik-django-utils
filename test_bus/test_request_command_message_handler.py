# # pylint: disable=protected-access
#
# import re
# from contextlib import ExitStack
# from unittest.mock import Mock, call, patch, PropertyMock
#
# import pytest
#
# from bus_local.utils.consumer import RequestCommandMessageHandler, CommandError
# from test_bus_local.models import TestRequestCommand, TestResponseCommand
# from test_bus_local.factories import TestEntity, TestRequestCommandFactory
# from test_bus_local.constants import (
#     TEST_REQUEST_COMMAND_QUEUE, TEST_REQUESTS_SETTING)
#
#
# @pytest.fixture
# def request_handler():
#     return RequestCommandMessageHandler(
#         Mock(name='body'), TEST_REQUEST_COMMAND_QUEUE,
#         Mock(name='event_captor'))
#
#
# class TestCommandMessageHandlerUpdateInstance:
#     def test_exec_command_call(self, request_handler):
#         for method in ['_process_command', '_payload', '_serializer', ]:
#             setattr(request_handler, method, Mock())
#
#         request_handler._update_instance()
#
#         assert request_handler._process_command.call_count == 1
#
#
# @pytest.mark.django_db
# class TestCommandMessageHandlerExecCommand:
#     def test_success(self, request_handler):
#         request = TestRequestCommandFactory()
#         with ExitStack() as stack:
#             stack.enter_context(patch.object(
#                 RequestCommandMessageHandler, '_instance',
#                 new_callable=PropertyMock, return_value=request))
#             stack.enter_context(patch.object(
#                 RequestCommandMessageHandler, '_model',
#                 new_callable=PropertyMock, return_value=type(request)))
#             stack.enter_context(patch.object(
#                 RequestCommandMessageHandler, 'requests_setting',
#                 new_callable=PropertyMock, return_value=TEST_REQUESTS_SETTING))
#             patched_apply_async = stack.enter_context(
#                 patch('celery.Task.apply_async'))
#             request_handler._process_command()
#             expected = [call(args=(request.uid, ))]
#             assert patched_apply_async.call_args_list == expected
#
#         response_command = TestResponseCommand.objects.get(
#             request=request)
#         assert response_command.status == 'accepted'
#         assert not response_command.error
#
#     def test_ignore_not_command(self, request_handler):
#         entity = TestEntity()
#         with ExitStack() as stack:
#             stack.enter_context(patch.object(
#                 RequestCommandMessageHandler, '_instance',
#                 new_callable=PropertyMock, return_value=entity))
#             stack.enter_context(patch.object(
#                 RequestCommandMessageHandler, '_model',
#                 new_callable=PropertyMock, return_value=type(entity)))
#             stack.enter_context(patch.object(
#                 RequestCommandMessageHandler, 'requests_setting',
#                 new_callable=PropertyMock, return_value=TEST_REQUESTS_SETTING))
#             request_handler._process_command()
#
#         assert not TestRequestCommand.objects.all().count()
#
#     def test_duplicate_request(self, request_handler):
#         with ExitStack() as stack:
#             request = TestRequestCommandFactory()
#             stack.enter_context(patch.object(
#                 RequestCommandMessageHandler, '_instance',
#                 new_callable=PropertyMock, return_value=request))
#             stack.enter_context(patch.object(
#                 RequestCommandMessageHandler, '_model',
#                 new_callable=PropertyMock, return_value=type(request)))
#             stack.enter_context(patch.object(
#                 RequestCommandMessageHandler, 'requests_setting',
#                 new_callable=PropertyMock, return_value=TEST_REQUESTS_SETTING))
#             request_handler._process_command()
#
#             error_message = (
#                 'Duplicate request guid for command `TestRequestCommand`.')
#             with pytest.raises(CommandError, match=re.escape(error_message)):
#                 request_handler._process_command()
