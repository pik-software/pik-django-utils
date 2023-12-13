# pylint: disable=protected-access

import re
from contextlib import ExitStack
from unittest.mock import Mock, call, patch, PropertyMock

from django.test import override_settings
import pytest

from pik.bus.consumer import RequestCommandMessageHandler, CommandError
from pik.bus.choices import REQUEST_COMMAND_STATUS_CHOICES as STATUSES
from test_bus.models import MyTestRequestCommand, MyTestResponseCommand
from test_bus.factories import (
    MyTestEntity, MyTestRequestCommandFactory, MyTestResponseCommandFactory)
from test_bus.constants import (
    TEST_QUEUE4REQUEST_COMMAND, TEST_QUEUE4ENTITY, TEST_RABBITMQ_RESPONSES,
    TEST_RABBITMQ_CONSUMES4REQUEST_COMMAND, TEST_RABBITMQ_CONSUMES4ENTITY)


class TestCommandMessageHandlerUpdateInstance:
    def test_exec_command_call(self):
        handler = RequestCommandMessageHandler(
            Mock(name='body'), Mock(name='queue'), Mock(name='captor'))

        for method in ['_process_command', '_payload', '_serializer', ]:
            setattr(handler, method, Mock())

        handler._update_instance()

        assert handler._process_command.call_count == 1


@pytest.mark.django_db
class TestCommandMessageHandlerExecCommand:
    @override_settings(
        RABBITMQ_CONSUMES=TEST_RABBITMQ_CONSUMES4REQUEST_COMMAND)
    @override_settings(RABBITMQ_RESPONSES=TEST_RABBITMQ_RESPONSES)
    @patch('test_bus.tasks.exec_command')
    def test_success(self, exec_command):
        handler = RequestCommandMessageHandler(
            Mock(name='body'), TEST_QUEUE4REQUEST_COMMAND, Mock(name='captor'))
        handler._queue_serializers_cache = {}  # To restore cache.
        request = MyTestRequestCommandFactory()
        with ExitStack() as stack:
            stack.enter_context(patch.object(
                RequestCommandMessageHandler, '_instance',
                new_callable=PropertyMock, return_value=request))
            stack.enter_context(patch.object(
                RequestCommandMessageHandler, '_model',
                new_callable=PropertyMock, return_value=type(request)))
            handler._process_command()
            expected = [call(request.uid)]
            assert exec_command.call_args_list == expected

        response_command = MyTestResponseCommand.objects.get(
            request=request)
        assert response_command.status == STATUSES.accepted
        assert not response_command.error

    @override_settings(RABBITMQ_CONSUMES=TEST_RABBITMQ_CONSUMES4ENTITY)
    def test_ignore_not_command(self):
        handler = RequestCommandMessageHandler(
            Mock(name='body'), TEST_QUEUE4ENTITY, Mock(name='captor'))
        handler._queue_serializers_cache = {}  # To restore cache.
        entity = MyTestEntity()
        with ExitStack() as stack:
            stack.enter_context(patch.object(
                RequestCommandMessageHandler, '_instance',
                new_callable=PropertyMock, return_value=entity))
            stack.enter_context(patch.object(
                RequestCommandMessageHandler, '_model',
                new_callable=PropertyMock, return_value=type(entity)))
            handler._process_command()

        assert not MyTestRequestCommand.objects.all().count()


@pytest.mark.django_db
class TestCommandMessageHandlerCheckRequest:
    def test_success(self):
        handler = RequestCommandMessageHandler(
            Mock(name='body'), Mock(name='queue'), Mock(name='captor'))
        request = MyTestRequestCommandFactory()
        with ExitStack() as stack:
            stack.enter_context(patch.object(
                RequestCommandMessageHandler, '_instance',
                new_callable=PropertyMock, return_value=request))
            handler._check_request(MyTestResponseCommand)

    def test_duplicate_request(self):
        handler = RequestCommandMessageHandler(
            Mock(name='body'), Mock(name='queue'), Mock(name='captor'))
        request = MyTestRequestCommandFactory()
        MyTestResponseCommandFactory(request=request)
        with ExitStack() as stack:
            stack.enter_context(patch.object(
                RequestCommandMessageHandler, '_instance',
                new_callable=PropertyMock, return_value=request))
            stack.enter_context(patch.object(
                RequestCommandMessageHandler, '_model',
                new_callable=PropertyMock, return_value=type(request)))
            error_message = (
                'Duplicate request guid for command `MyTestRequestCommand`.')
            with pytest.raises(CommandError, match=re.escape(error_message)):
                handler._check_request(MyTestResponseCommand)
