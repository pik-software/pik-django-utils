import uuid
from io import BytesIO
import json
from pprint import pformat
from unittest.mock import Mock, patch, call, PropertyMock
from uuid import UUID

import pytest
from django.db.models import Manager
from django.core.cache import cache
from rest_framework.exceptions import ParseError, ValidationError, ErrorDetail
from rest_framework.fields import DateTimeField
from rest_framework.serializers import CharField

from pik.api.serializers import StandardizedModelSerializer
from pik.bus.consumer import MessageHandler, MessageConsumer
from pik.bus.exceptions import SerializerMissingError
from pik.bus.models import PIKMessageException
from test_core_models.models import RegularModel, RemovableRegularDepended


class RegularModelSerializer(StandardizedModelSerializer):
    name = CharField()

    class Meta:
        model = RegularModel
        fields = ('guid', 'name')


class RemovableRegularDependedSerializer(StandardizedModelSerializer):
    dependence = RegularModelSerializer(fields=('guid', 'type'))
    created = DateTimeField(required=False)

    class Meta:
        model = RemovableRegularDepended
        fields = ('guid', 'created', 'dependence')


class RegularDatedModelSerializer(RegularModelSerializer):
    created = DateTimeField(required=False)

    class Meta:
        model = RegularModel
        fields = ('guid', 'created', 'name')


class TestMessageHandlerFetch:
    @staticmethod
    def test_ok():
        handler = MessageHandler(
            b'{"message": {}}', Mock(name='queue'), Mock(name='event_captor'))
        handler._fetch_payload()  # noqa: protected-access
        assert handler._payload == {}  # noqa: protected-access

    @staticmethod
    def test_invalid_json():
        handler = MessageHandler(
            b'', Mock(name='queue'), Mock(name='event_captor'))
        with pytest.raises(ParseError):
            handler._fetch_payload()  # noqa: protected-access
        assert handler._payload is None  # noqa: protected-access

    @staticmethod
    def test_message_missing():
        handler = MessageHandler(
            b'{}', Mock(name='queue'), Mock(name='event_captor'))
        with pytest.raises(KeyError):
            handler._fetch_payload()  # noqa: protected-access
        assert handler._payload is None  # noqa: protected-access

    @staticmethod
    def test_not_bytes():
        handler = MessageHandler(
            42, Mock(name='queue'), Mock(name='event_captor'))
        with pytest.raises(TypeError):
            handler._fetch_payload()  # noqa: protected-access
        assert handler._payload is None  # noqa: protected-access


class TestMessageHandlerPrepare:
    @staticmethod
    def test_ok():
        handler = MessageHandler(
            Mock(name='message'), Mock(name='queue'),
            Mock(name='event_captor'))
        handler._payload = {'someValue': 42}  # noqa: protected-access
        with patch.object(MessageHandler, '_serializer_cls', Mock(
                underscorize_hook=Mock(
                    side_effect=lambda x: x))) as serializer:
            handler._prepare_payload()  # noqa: protected-access
        assert handler._payload == {'some_value': 42}  # noqa: protected-access
        assert serializer.underscorize_hook.called

    @staticmethod
    def test_serializer_missing():
        handler = MessageHandler(
            Mock(name='message'), Mock(name='queue'),
            Mock(name='event_captor'))
        handler._payload = {'someValue': 42}  # noqa: protected-access
        with pytest.raises(SerializerMissingError):
            handler._prepare_payload()  # noqa: protected-access
        assert handler._payload == {'some_value': 42}  # noqa: protected-access

    @staticmethod
    def test_invalid_payload():
        handler = MessageHandler(
            Mock(name='message'), Mock(name='queue'),
            Mock(name='event_captor'))
        payload = Exception()
        handler._payload = payload  # noqa: protected-access
        with patch.object(
                MessageHandler, '_serializer_cls',
                Mock(underscorize_hook=Mock(side_effect=lambda x: x))):
            handler._prepare_payload()  # noqa: protected-access
        assert handler._payload == payload  # noqa: protected-access


class TestMessageHandlerUpdateInstance:
    @staticmethod
    @pytest.mark.django_db
    def test_instance_exists():
        RegularModel(
            uid=UUID('b24d988e-42aa-477d-a8c3-a88b127b9b31'),
            name='Existing').save()
        handler = MessageHandler(
            Mock(name='message'), Mock(name='queue'),
            Mock(name='event_captor'))
        handler._payload = {'guid': 'b24d988e-42aa-477d-a8c3-a88b127b9b31'}  # noqa: protected-access
        with patch.object(
                MessageHandler, '_serializer_cls', RegularModelSerializer):
            assert isinstance(handler._instance, RegularModel)  # noqa: protected-access
            assert handler._instance.uid == UUID(  # noqa: protected-access
                'b24d988e-42aa-477d-a8c3-a88b127b9b31')
            assert not handler._instance._state.adding  # noqa: protected-access

    @staticmethod
    @pytest.mark.django_db
    def test_instance_missing():
        guid = str(uuid.uuid4())
        handler = MessageHandler(
            Mock(name='message'), Mock(name='queue'),
            Mock(name='event_captor'))
        handler._payload = {'guid': guid}  # noqa: protected-access
        with patch.object(
                MessageHandler, '_serializer_cls', RegularModelSerializer):
            assert isinstance(handler._instance, RegularModel)  # noqa: protected-access
            assert handler._instance.uid == guid  # noqa: protected-access
            assert handler._instance._state.adding  # noqa: protected-access

    @staticmethod
    def test_queryset():
        handler = MessageHandler(
            Mock(name='message'), Mock(name='queue'),
            Mock(name='event_captor'))
        with patch.object(
                MessageHandler, '_serializer_cls', RegularModelSerializer):
            assert isinstance(handler._queryset, Manager)  # noqa: protected-access

    @staticmethod
    def test_model():
        handler = MessageHandler(
            Mock(name='message'), Mock(name='queue'),
            Mock(name='event_captor'))
        with patch.object(
                MessageHandler, '_serializer_cls', RegularModelSerializer):
            assert handler._model == RegularModel  # noqa: protected-access

    @staticmethod
    @pytest.mark.django_db
    def test_ok():
        handler = MessageHandler(
            Mock(name='message'), Mock(name='queue'),
            Mock(name='event_captor'))
        handler._payload = {  # noqa: protected-access
            'guid': 'b24d988e-42aa-477d-a8c3-a88b127b9b31', 'name': 'Test'}
        with patch.object(
                MessageHandler, '_serializer_cls', RegularModelSerializer):
                    handler._update_instance()  # noqa: protected-access

        assert list(RegularModel.objects.values('name', 'uid')) == [{
            'uid': UUID('b24d988e-42aa-477d-a8c3-a88b127b9b31'),
            'name': 'Test'
        }]

    @staticmethod
    @pytest.mark.django_db
    @patch.object(
        MessageHandler, '_serializer_cls',
        RemovableRegularDependedSerializer)
    def test_missing_depended_model():
        handler = MessageHandler(
            Mock(name='message'), Mock(name='queue'),
            Mock(name='event_captor'))
        handler._payload = {  # noqa: protected-access
            'guid': 'b24d988e-42aa-477d-a8c3-a88b127b9b31',
            'dependence': {
                'guid': 'b24d988e-42aa-477d-a8c3-a88b127b9b31',
                'type': 'regularmodel'}}

        with patch.object(
                MessageHandler, '_instance', RemovableRegularDepended()):
            with pytest.raises(ValidationError) as exc:
                handler._update_instance()  # noqa: protected-access
            assert exc.value.detail == {'dependence': [
                ErrorDetail(
                    string=('Недопустимый guid '
                            '"b24d988e-42aa-477d-a8c3-a88b127b9b31" - '
                            'объект не существует.'),
                    code='does_not_exist')]}

    @staticmethod
    @pytest.mark.django_db
    @patch.object(
        MessageHandler, '_serializer_cls',
        RemovableRegularDependedSerializer)
    def test_multiple_error_model():
        handler = MessageHandler(
            Mock(name='message'), Mock(name='queue'),
            Mock(name='event_captor'))
        handler._payload = {  # noqa: protected-access
            'guid': 'b24d988e-42aa-477d-a8c3-a88b127b9b31',
            'created': 'zzzz',
            'dependence': {
                'guid': 'b24d988e-42aa-477d-a8c3-a88b127b9b31',
                'type': 'regularmodel'}}

        with patch.object(
                MessageHandler, '_instance', RemovableRegularDepended()):
            with pytest.raises(ValidationError) as exc:
                handler._update_instance()  # noqa: protected-access
            assert exc.value.detail == {'created': [ErrorDetail(string=(
                'Datetime has wrong format. Use one of these formats '
                'instead: YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].'),
                code='invalid')], 'dependence': [ErrorDetail(string=(
                    'Недопустимый guid "b24d988e-42aa-477d-a8c3-a88b127b9b31" '
                    '- объект не существует.'), code='does_not_exist')]}

    @staticmethod
    @pytest.mark.django_db
    def test_cache_lock():
        uid = str(uuid.uuid4())
        handler = MessageHandler(
            Mock(name='message'), 'test_queue', Mock(name='event_captor'))
        handler._serializer = Mock()
        cache.lock = Mock(wraps=cache.lock)
        with patch.object(MessageHandler, '_uid', uid):
            handler._update_instance()

        expected = [
            call(f"bus-test_queue-{uid}", timeout=60)]
        assert cache.lock.mock_calls == expected


class TestMessageHandlerQueueSerializers:
    TEST_QUEUE_SERIALIZERS_CACHE = {'test_key': 'test_value'}

    @pytest.mark.django_db
    @patch.object(
        MessageHandler, '_queue_serializers',
        return_value=TEST_QUEUE_SERIALIZERS_CACHE, new_callable=PropertyMock)
    def test_queue_serializers_cache(self, _queue_serializers):
        handler1 = MessageHandler(
            Mock(name='message'), Mock(name='queue'),
            Mock(name='event_captor'))
        queue_serializers = handler1.queue_serializers
        assert len(_queue_serializers.mock_calls) == 1
        assert queue_serializers == self.TEST_QUEUE_SERIALIZERS_CACHE

        handler2 = MessageHandler(
            Mock(name='message'), Mock(name='queue'),
            Mock(name='event_captor'))
        queue_serializers = handler2.queue_serializers
        assert len(_queue_serializers.mock_calls) == 1
        assert queue_serializers == self.TEST_QUEUE_SERIALIZERS_CACHE


@pytest.mark.django_db
class TestMessageHandlerException:
    @staticmethod
    def test_unexpected_error():
        PIKMessageException(
            uid='dbef014c-1ece-f8f9-9e5e-fa78cf01680d',
            exception='',
            queue='test_queue',
            body_hash='dbef014c1ecef8f99e5efa78cf01680d2e0aa42f').save()
        handler = MessageHandler(
            b'test_message', 'test_queue', Mock(name='event_captor'))
        handler._capture_exception(Exception('test'))  # noqa: protected-access
        expected = [{
            'exception': {'code': 'Exception', 'message': 'test'},
            'uid': UUID('dbef014c-1ece-f8f9-9e5e-fa78cf01680d'),
            'exception_message': 'test', 'exception_type': 'Exception',
            'queue': 'test_queue'}]
        assert list(PIKMessageException.objects.values(
            'queue', 'exception', 'exception_type', 'exception_message',
            'uid')) == expected
        message = PIKMessageException.objects.values_list('message').first()[0]
        assert BytesIO(message).read() == b'test_message'

    @staticmethod
    def test_validation_error():
        PIKMessageException(
            uid='dbef014c-1ece-f8f9-9e5e-fa78cf01680d',
            entity_uid='dbef014c-1ece-f8f9-9e5e-fa78cf01680d',
            exception='', queue='test_queue').save()
        handler = MessageHandler(
            b'test_message', 'test_queue', Mock(name='event_captor'))
        handler._payload = {'guid': 'dbef014c-1ece-f8f9-9e5e-fa78cf01680d'}  # noqa: protected-access
        handler._capture_exception(ValidationError({'name': [  # noqa: protected-access
            ErrorDetail(string='This field is required.', code='required')]}))
        expected = [{
            'exception': {
                'code': 'invalid', 'detail': {'name': [{
                    'code': 'required',
                    'message': 'This field is required.'}]},
                'message': 'Invalid input.'},
            'exception_message': 'Invalid input.',
            'exception_type': 'invalid',
            'queue': 'test_queue'}]
        assert list(PIKMessageException.objects.values(
            'exception', 'exception_message', 'exception_type',
            'queue')) == expected
        message = PIKMessageException.objects.values_list('message').first()[0]
        assert BytesIO(message).read() == b'test_message'

    @staticmethod
    def test_dependency_error():
        PIKMessageException(
            uid='dbef014c-1ece-f8f9-9e5e-fa78cf01680d',
            entity_uid='dbef014c-1ece-f8f9-9e5e-fa78cf01680d',
            exception='', queue='test_queue').save()
        handler = MessageHandler(
            b'test_message', 'test_queue', Mock(name='event_captor'))
        handler._payload = {  # noqa: protected-access
            'guid': 'dbef014c-1ece-f8f9-9e5e-fa78cf01680d',
            'dependence': {'guid': 'DependencyGuid', 'type': 'DependencyType'}}
        handler._capture_exception(ValidationError({'created': [  # noqa: protected-access
            ErrorDetail(string=(
                'Datetime has wrong format. Use one of these formats instead: '
                'YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].'),
                code='invalid')],
            'dependence': [ErrorDetail(string=(
                'Недопустимый guid "b24d988e-42aa-477d-a8c3-a88b127b9b31"'
                ' - объект не существует.'), code='does_not_exist')]}))
        expected = [{
            'dependencies': {'DependencyType': 'DependencyGuid'},
            'exception': {'code': 'invalid', 'detail': {'created': [{
                'code': 'invalid', 'message': (
                    'Datetime has wrong format. Use one of these formats '
                    'instead: '
                    'YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].')}],
                'dependence': [{'code': 'does_not_exist', 'message': (
                    'Недопустимый guid '
                    '"b24d988e-42aa-477d-a8c3-a88b127b9b31" - объект '
                    'не существует.')}]}, 'message': 'Invalid input.'},
            'exception_message': 'Invalid input.',
            'exception_type': 'invalid',
            'queue': 'test_queue'}]
        assert list(PIKMessageException.objects.values(
            'queue', 'exception', 'exception_type',
            'exception_message', 'dependencies')) == expected

        message = PIKMessageException.objects.values_list('message').first()[0]
        assert BytesIO(message).read() == b'test_message'

    @staticmethod
    @pytest.mark.django_db
    def test_validation_error_invalid_uuid():
        handler = MessageHandler(
            b'test_message', 'test_queue', Mock(name='event_captor'))
        handler._payload = {'guid': 'invalid'}  # noqa: protected-access

        exc = ValidationError({'uuid': [ErrorDetail(
            string='“invalid” is not a valid UUID.', code='invalid')]})
        handler._capture_exception(exc)  # noqa: protected-access

        excepted = [{
            'exception': {'code': 'invalid',
                          'detail': {'uuid': [{
                              'code': 'invalid',
                              'message': '“invalid” is not a valid UUID.'}]},
                          'message': 'Invalid input.'},
            'exception_message': 'Invalid input.',
            'exception_type': 'invalid',
            'queue': 'test_queue'}]
        assert list(PIKMessageException.objects.values(
            'queue', 'exception', 'exception_type',
            'exception_message')) == excepted

        message = PIKMessageException.objects.values_list('message').first()[0]
        assert BytesIO(message).read() == b'test_message'


@pytest.mark.django_db
class TestMessageHandlerDependencies:
    @staticmethod
    def test_missing_dependency():
        handler = MessageHandler(
            Mock(name='message'), Mock(name='queue'),
            Mock(name='event_captor'))
        handler._payload = {'guid': 42, 'type': 'RegularModel'}  # noqa: protected-access
        handler._process_dependants()  # noqa: protected-access

    @staticmethod
    @patch.object(MessageHandler, '_serializer_cls', RegularModelSerializer)
    def test_process_dependency():
        (PIKMessageException(
            message=json.dumps({'message': {
                'type': 'Dependency',
                'name': 'Dependency',
                'guid': '00000000-0000-0000-0000-000000000000'
            }}).encode('utf8'),
            exception='',
            queue='test_queue',
            dependencies={
                'DependantModel': '11111111-1111-1111-1111-111111111111'})
         .save())

        handler = MessageHandler(
            Mock(name='message'), Mock(name='queue'),
            Mock(name='event_captor'))
        handler._payload = {  # noqa: protected-access
            'guid': '11111111-1111-1111-1111-111111111111',
            'type': 'DependantModel'}
        handler._process_dependants()  # noqa: protected-access

        assert list(RegularModel.objects.values('uid', 'name')) == [{
            'uid': UUID('00000000-0000-0000-0000-000000000000'),
            'name': 'Dependency'}]
        assert PIKMessageException.objects.count() == 0


class TestMessageConsumerEvents:
    @staticmethod
    @patch(
        'pik.bus.consumer.MessageHandler.envelope',
        property(Mock(side_effect=ZeroDivisionError)))
    def test_fail_invalid():
        event_captor = Mock(name='event_captor')
        message_consumer = MessageConsumer(
            'test_url', 'test_consumer', 'test_queue', event_captor)

        message_consumer._handle_message(  # noqa: protected-access
            Mock(name='test_channel'), Mock(name='test_meth'), {},
            b'test_message', 'test_queue')
        expected = pformat([call(
            event='consumption', entity_type=None, entity_guid=None,
            transactionGUID=None, transactionMessageCount=None, success=False,
            error=ZeroDivisionError())])
        assert pformat(event_captor.capture.call_args_list) == expected

    @staticmethod
    @pytest.mark.django_db
    @patch('pik.bus.consumer.MessageHandler._serializer_cls', Mock())
    def test_success_consumption():
        event_captor = Mock(name='event_captor')
        message_consumer = MessageConsumer(
            'test_url', 'test_consumer', 'test_queue', event_captor)

        envelope = {
            'message': {
                'type': 'TestType',
                'guid': 'ABC...'}}
        with patch.object(MessageHandler, 'envelope', property(Mock(
                return_value=envelope))):
            message_consumer._handle_message(  # noqa: protected-access
                Mock(name='test_channel'), Mock(name='test_method'), {},
                b'test_message', 'test_queue')

        expected = pformat([call(
            event='consumption', entity_type='TestType', entity_guid='ABC...',
            transactionGUID=None, transactionMessageCount=None, success=True,
            error=None)])
        assert pformat(event_captor.capture.call_args_list) == expected

    @staticmethod
    @pytest.mark.django_db
    @patch('pik.bus.consumer.MessageHandler._serializer', Mock())
    def test_success_consumption_transactions():
        event_captor = Mock(name='event_captor')
        message_consumer = MessageConsumer(
            'test_url', 'test_consumer', 'test_queue', event_captor)

        envelope = {
            'headers': {
                'transactionGUID': 'DEF...',
                'transactionMessageCount': 42},
            'message': {
                'type': 'TestType',
                'guid': 'ABC...'}}
        with patch.object(MessageHandler, 'envelope', property(Mock(
                return_value=envelope))):
            message_consumer._handle_message(  # noqa: protected-access
                Mock(name='test_channel'), Mock(name='test_method'), {},
                b'test_message', 'test_queue')

        expected = pformat([call(
            event='consumption', entity_type='TestType', entity_guid='ABC...',
            transactionGUID='DEF...', transactionMessageCount=42,
            success=True, error=None)])
        assert pformat(event_captor.capture.call_args_list) == expected


class TestMessageHandlerEvents:
    @staticmethod
    @patch('pik.bus.consumer.MessageHandler._capture_exception', Mock())
    @patch(
        'pik.bus.consumer.MessageHandler._fetch_payload',
        Mock(side_effect=ZeroDivisionError))
    def test_fail_invalid():
        event_captor = Mock(name='event_captor')
        message_handler = MessageHandler(
            b'test_message', 'test_queue', event_captor)

        envelope = {'message': {}}
        with patch.object(MessageHandler, 'envelope', property(
                Mock(return_value=envelope))):
            message_handler.handle()

        expected = pformat([call(
            event='deserialization', entity_type=None, entity_guid=None,
            transactionGUID=None, transactionMessageCount=None,
            success=False, error=ZeroDivisionError())])
        assert pformat(event_captor.capture.call_args_list) == expected

    @staticmethod
    @patch('pik.bus.consumer.MessageHandler._capture_exception', Mock())
    @patch(
        'pik.bus.consumer.MessageHandler._fetch_payload',
        Mock(side_effect=ZeroDivisionError))
    def test_failed_deserialization():
        event_captor = Mock(name='event_captor')
        message_handler = MessageHandler(
            b'test_message', 'test_queue', event_captor)

        envelope = {'message': {'guid': 'ABC...', 'type': 'TestType'}}
        with patch.object(MessageHandler, 'envelope', property(
                Mock(return_value=envelope))):
            message_handler.handle()

        expected = pformat([call(
            event='deserialization', entity_type='TestType',
            entity_guid='ABC...', transactionGUID=None,
            transactionMessageCount=None, success=False,
            error=ZeroDivisionError())])
        assert pformat(event_captor.capture.call_args_list) == expected

    @staticmethod
    @pytest.mark.django_db
    @patch('pik.bus.consumer.MessageHandler._serializer_cls', Mock())
    @patch('pik.bus.consumer.MessageHandler._update_instance', Mock())
    @patch('pik.bus.consumer.MessageHandler._process_dependants', Mock())
    @patch('pik.bus.consumer.MessageHandler._capture_exception', Mock())
    def test_success_deserialization():
        event_captor = Mock(name='event_captor')
        message_handler = MessageHandler(
            b'test_message', 'test_queue', event_captor)

        envelope = {'message': {'guid': 'ABC...', 'type': 'TestType'}}
        with patch.object(MessageHandler, 'envelope', property(
                Mock(return_value=envelope))):
            message_handler.handle()

        expected = pformat([call(
            event='deserialization', entity_type='TestType',
            entity_guid='ABC...', transactionGUID=None,
            transactionMessageCount=None, success=True, error=None)])
        assert pformat(event_captor.capture.call_args_list) == expected

    @staticmethod
    @patch('pik.bus.consumer.MessageHandler._capture_exception', Mock())
    @patch(
        'pik.bus.consumer.MessageHandler._fetch_payload',
        Mock(side_effect=ZeroDivisionError))
    def test_failed_deserialization_transaction():
        event_captor = Mock(name='event_captor')
        message_handler = MessageHandler(
            b'test_message', 'test_queue', event_captor)

        envelope = {
            'headers': {
                'transactionGUID': 'DCEBA...',
                'transactionMessageCount': 10},
            'message': {
                'guid': 'ABC...', 'type': 'TestType'}}
        with patch.object(MessageHandler, 'envelope', property(
                Mock(return_value=envelope))):
            message_handler.handle()

        expected = pformat([call(
            event='deserialization', entity_type='TestType',
            entity_guid='ABC...',
            transactionGUID='DCEBA...', transactionMessageCount=10,
            success=False, error=ZeroDivisionError())])
        assert pformat(event_captor.capture.call_args_list) == expected


class TestMessageHandlerMultipleErrors:
    @staticmethod
    @pytest.mark.django_db
    def test_delete_success():
        message = json.dumps({'message': {
            'type': 'test_queue',
            'name': 'test_queue',
            'guid': '99999999-9999-9999-9999-999999999999'
        }}).encode('utf8')
        queue = 'test_queue'
        exc_data = {
            'uid': '00000000-0000-0000-0000-000000000000',
            'entity_uid': '99999999-9999-9999-9999-999999999999',
            'body_hash': 'b732cb833f4b2db280e371a1ad19c9f3dd8abdf5',
            'queue': queue,
            'message': message,
            'exception': {
                'code': 'invalid',
                'detail': {
                    'name': [
                        {'code': 'null',
                         'message': 'Это поле не может быть пустым.'}]}},
            'exception_type': 'invalid',
            'exception_message': 'Invalid input.'}
        PIKMessageException(**exc_data).save()
        handler = MessageHandler(
            message, queue,
            Mock(name='event_captor'))
        handler._register_success()  # noqa: protected-access
        assert PIKMessageException.objects.count() == 0

    @staticmethod
    @pytest.mark.django_db
    def test_system_error_after_existing_system_error():
        message = json.dumps({'message': {
            'type': 'test_queue',
            'name': 'test_queue',
            'guid': '99999999-9999-9999-9999-999999999999'
        }}).encode('utf8')
        queue = 'test_queue'
        exc_data = {
            'uid': '00000000-0000-0000-0000-000000000000',
            'entity_uid': '99999999-9999-9999-9999-999999999999',
            'body_hash': 'b732cb833f4b2db280e371a1ad19c9f3dd8abdf5',
            'queue': queue,
            'message': message,
            'exception': {
                'code': 'ConnectionError',
                'message': (
                    'Error 111 connecting to service-redis:6379. '
                    'Connection refused.')},
            'exception_type': 'ConnectionError',
            'exception_message': (
                'Error 111 connecting to service-redis:6379. '
                'Connection refused.')}
        PIKMessageException(**exc_data).save()
        handler = MessageHandler(
            message, queue,
            Mock(name='event_captor'))
        handler.handle()
        messages_qs = PIKMessageException.objects.all()
        assert messages_qs.count() == 1
        expected = {
            'uid': UUID('00000000-0000-0000-0000-000000000000'),
            'entity_uid': UUID('99999999-9999-9999-9999-999999999999'),
            'body_hash': 'b732cb833f4b2db280e371a1ad19c9f3dd8abdf5',
            'queue': 'test_queue',
            'exception': {
                'code': 'SerializerMissingError',
                'message': 'Unable to find serializer for `test_queue`'},
            'exception_type': 'SerializerMissingError',
            'exception_message': 'Unable to find serializer for `test_queue`'}
        assert (
            messages_qs.values(
                'uid', 'entity_uid', 'body_hash', 'queue',
                'exception', 'exception_type', 'exception_message')
            .first()) == expected
        assert (bytes(
            messages_qs.values_list('message', flat=True)
            .first()) == message)

    @staticmethod
    @pytest.mark.django_db
    def test_system_error_after_existing_validation_error():
        message = json.dumps({'message': {
            'type': 'test_queue',
            'name': 'test_queue',
            'guid': '99999999-9999-9999-9999-999999999999'
        }}).encode('utf8')
        queue = 'test_queue'
        exc_data = {
            'uid': '00000000-0000-0000-0000-000000000000',
            'entity_uid': '99999999-9999-9999-9999-999999999999',
            'body_hash': 'b732cb833f4b2db280e371a1ad19c9f3dd8abdf5',
            'queue': queue,
            'message': message,
            'exception': {
                'code': 'invalid',
                'detail': {
                    'name': [
                        {'code': 'null',
                         'message': 'Это поле не может быть пустым.'}]}},
            'exception_type': 'invalid',
            'exception_message': 'Invalid input.'}
        PIKMessageException(**exc_data).save()
        handler = MessageHandler(
            message, queue,
            Mock(name='event_captor'))
        handler.handle()
        messages_qs = PIKMessageException.objects.all()
        assert messages_qs.count() == 1
        expected = {
            'uid': UUID('00000000-0000-0000-0000-000000000000'),
            'entity_uid': UUID('99999999-9999-9999-9999-999999999999'),
            'body_hash': 'b732cb833f4b2db280e371a1ad19c9f3dd8abdf5',
            'queue': 'test_queue',
            'exception': {
                'code': 'SerializerMissingError',
                'message': 'Unable to find serializer for `test_queue`'},
            'exception_type': 'SerializerMissingError',
            'exception_message': 'Unable to find serializer for `test_queue`'}
        assert (
            messages_qs.values(
                'uid', 'entity_uid', 'body_hash', 'queue',
                'exception', 'exception_type', 'exception_message')
            .first()) == expected
        assert (bytes(
            messages_qs.values_list('message', flat=True)
            .first()) == message)

    @staticmethod
    @pytest.mark.django_db
    @patch.object(
        MessageHandler, '_serializer_cls',
        RegularDatedModelSerializer)
    def test_validation_error_after_existing_validation_error():
        message = json.dumps({'message': {
            'created': 'created_date',
            'name': 'test_queue',
            'guid': '99999999-9999-9999-9999-999999999999'
        }}).encode('utf8')
        queue = 'test_queue'
        exc_data = {
            'uid': '00000000-0000-0000-0000-000000000000',
            'entity_uid': '99999999-9999-9999-9999-999999999999',
            'body_hash': 'db16834ab244d557e098ffa4482eb304cfbaf780',
            'queue': queue,
            'message': message,
            'exception': {
                'code': 'invalid',
                'detail': {
                    'name': [
                        {'code': 'null',
                         'message': 'Это поле не может быть пустым.'}]}},
            'exception_type': 'invalid',
            'exception_message': 'Invalid input.'}
        PIKMessageException(**exc_data).save()
        handler = MessageHandler(
            message, queue,
            Mock(name='event_captor'))
        handler.handle()
        messages_qs = PIKMessageException.objects.all()
        assert messages_qs.count() == 1
        expected = {
            'uid': UUID('00000000-0000-0000-0000-000000000000'),
            'entity_uid': UUID('99999999-9999-9999-9999-999999999999'),
            'body_hash': 'db16834ab244d557e098ffa4482eb304cfbaf780',
            'queue': 'test_queue',
            'exception': {
                'code': 'invalid',
                'detail': {
                    'created': [{
                        'code': 'invalid',
                        'message': (
                            'Datetime has wrong format. '
                            'Use one of these formats '
                            'instead: '
                            'YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].'
                        )}]},
                'message': 'Invalid input.'},
            'exception_message': 'Invalid input.',
            'exception_type': 'invalid'}
        assert (
            messages_qs.values(
                'uid', 'entity_uid', 'body_hash', 'queue',
                'exception', 'exception_type', 'exception_message')
            .first()) == expected
        assert (bytes(
            messages_qs.values_list('message', flat=True)
            .first()) == message)

    @staticmethod
    @pytest.mark.django_db
    @patch.object(
        MessageHandler, '_serializer_cls',
        RegularDatedModelSerializer)
    def test_validation_error_after_existing_system_error():
        message = json.dumps({'message': {
            'created': 'created_date',
            'name': 'test_queue',
            'guid': '99999999-9999-9999-9999-999999999999'
        }}).encode('utf8')
        queue = 'test_queue'
        exc_data = {
            'uid': '00000000-0000-0000-0000-000000000000',
            'entity_uid': '99999999-9999-9999-9999-999999999999',
            'body_hash': 'db16834ab244d557e098ffa4482eb304cfbaf780',
            'queue': queue,
            'message': message,
            'exception': {
                'code': 'ConnectionError',
                'message': (
                    'Error 111 connecting to service-redis:6379. '
                    'Connection refused.')},
            'exception_type': 'ConnectionError',
            'exception_message': (
                'Error 111 connecting to service-redis:6379. '
                'Connection refused.')}
        PIKMessageException(**exc_data).save()
        handler = MessageHandler(
            message, queue,
            Mock(name='event_captor'))
        handler.handle()
        messages_qs = PIKMessageException.objects.all()
        assert messages_qs.count() == 1
        expected = {
            'uid': UUID('00000000-0000-0000-0000-000000000000'),
            'entity_uid': UUID('99999999-9999-9999-9999-999999999999'),
            'body_hash': 'db16834ab244d557e098ffa4482eb304cfbaf780',
            'queue': 'test_queue',
            'exception': {
                'code': 'invalid',
                'detail': {
                    'created': [{
                        'code': 'invalid',
                        'message': (
                            'Datetime has wrong format. '
                            'Use one of these formats '
                            'instead: '
                            'YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].'
                        )}]},
                'message': 'Invalid input.'},
            'exception_message': 'Invalid input.',
            'exception_type': 'invalid'}
        assert (
            messages_qs.values(
                'uid', 'entity_uid', 'body_hash', 'queue',
                'exception', 'exception_type', 'exception_message')
            .first()) == expected
        assert (bytes(
            messages_qs.values_list('message', flat=True)
            .first()) == message)

    @staticmethod
    @pytest.mark.django_db
    def test_system_error_after_existing_validation_and_system_errors():
        message = json.dumps({'message': {
            'type': 'test_queue',
            'name': 'test_queue',
            'guid': '99999999-9999-9999-9999-999999999999'
        }}).encode('utf8')
        queue = 'test_queue'
        exc_data_system = {
            'uid': '00000000-0000-0000-0000-000000000000',
            'entity_uid': None,
            'body_hash': 'b732cb833f4b2db280e371a1ad19c9f3dd8abdf5',
            'queue': queue,
            'message': message,
            'exception': {
                'code': 'ConnectionError',
                'message': (
                    'Error 111 connecting to service-redis:6379. '
                    'Connection refused.')},
            'exception_type': 'ConnectionError',
            'exception_message': (
                'Error 111 connecting to service-redis:6379. '
                'Connection refused.')}
        exc_data_validation = {
            'uid': '11111111-1111-1111-1111-111111111111',
            'entity_uid': '99999999-9999-9999-9999-999999999999',
            'body_hash': None,
            'queue': queue,
            'message': message,
            'exception': {
                'code': 'invalid',
                'detail': {
                    'name': [
                        {'code': 'null',
                         'message': 'Это поле не может быть пустым.'}]}},
            'exception_type': 'invalid',
            'exception_message': 'Invalid input.'}
        PIKMessageException(**exc_data_system).save()
        PIKMessageException(**exc_data_validation).save()
        handler = MessageHandler(
            message, queue, Mock(name='event_captor'))
        handler.handle()
        messages_qs = PIKMessageException.objects.all()
        assert messages_qs.count() == 1
        expected = {
            'uid': UUID('11111111-1111-1111-1111-111111111111'),
            'entity_uid': UUID('99999999-9999-9999-9999-999999999999'),
            'body_hash': None,
            'queue': 'test_queue',
            'exception': {
                'code': 'SerializerMissingError',
                'message': 'Unable to find serializer for `test_queue`'},
            'exception_type': 'SerializerMissingError',
            'exception_message': 'Unable to find serializer for `test_queue`'}
        assert (
            messages_qs.values(
                'uid', 'entity_uid', 'body_hash', 'queue',
                'exception', 'exception_type', 'exception_message')
            .first()) == expected
        assert (bytes(
            messages_qs.values_list('message', flat=True)
            .first()) == message)

    @staticmethod
    @pytest.mark.django_db
    @patch.object(
        MessageHandler, '_serializer_cls',
        RegularDatedModelSerializer)
    def test_validation_error_after_existing_validation_and_system_errors():
        message = json.dumps({'message': {
            'created': 'created_date',
            'name': 'test_queue',
            'guid': '99999999-9999-9999-9999-999999999999'
        }}).encode('utf8')
        queue = 'test_queue'
        exc_data_validation = {
            'uid': '00000000-0000-0000-0000-000000000000',
            'entity_uid': None,
            'body_hash': 'db16834ab244d557e098ffa4482eb304cfbaf780',
            'queue': queue,
            'message': message,
            'exception': {
                'code': 'invalid',
                'detail': {
                    'name': [
                        {'code': 'null',
                         'message': 'Это поле не может быть пустым.'}]}},
            'exception_type': 'invalid',
            'exception_message': 'Invalid input.'}
        exc_data_system = {
            'uid': '11111111-1111-1111-1111-111111111111',
            'entity_uid': '99999999-9999-9999-9999-999999999999',
            'body_hash': None,
            'queue': queue,
            'message': message,
            'exception': {
                'code': 'ConnectionError',
                'message': (
                    'Error 111 connecting to service-redis:6379. '
                    'Connection refused.')},
            'exception_type': 'ConnectionError',
            'exception_message': (
                'Error 111 connecting to service-redis:6379. '
                'Connection refused.')}
        PIKMessageException(**exc_data_validation).save()
        PIKMessageException(**exc_data_system).save()
        handler = MessageHandler(
            message, queue,
            Mock(name='event_captor'))
        handler.handle()
        messages_qs = PIKMessageException.objects.all()
        assert messages_qs.count() == 1
        expected = {
            'uid': UUID('11111111-1111-1111-1111-111111111111'),
            'entity_uid': UUID('99999999-9999-9999-9999-999999999999'),
            'body_hash': None,
            'queue': 'test_queue',
            'exception': {
                'code': 'invalid',
                'detail': {
                    'created': [{
                        'code': 'invalid',
                        'message': (
                            'Datetime has wrong format. '
                            'Use one of these formats '
                            'instead: '
                            'YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].'
                        )}]},
                'message': 'Invalid input.'},
            'exception_message': 'Invalid input.',
            'exception_type': 'invalid'}
        assert (
            messages_qs.values(
                'uid', 'entity_uid', 'body_hash', 'queue',
                'exception', 'exception_type', 'exception_message')
            .first()) == expected
        assert (bytes(
            messages_qs.values_list('message', flat=True)
            .first()) == message)
