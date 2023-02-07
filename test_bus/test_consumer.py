from io import BytesIO
import json
from pprint import pformat
from unittest.mock import Mock, patch, call
from uuid import UUID

import pytest
from django.db.models import Manager
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
        with patch.object(MessageHandler, '_serializer_class', Mock(
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
        handler._serializers = {}  # noqa: protected-access
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
                MessageHandler, '_serializer_class',
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
                MessageHandler, '_serializer_class', RegularModelSerializer):
            assert isinstance(handler._instance, RegularModel)  # noqa: protected-access
            assert handler._instance.uid == UUID(  # noqa: protected-access
                'b24d988e-42aa-477d-a8c3-a88b127b9b31')
            assert not handler._instance._state.adding  # noqa: protected-access

    @staticmethod
    @pytest.mark.django_db
    def test_instance_missing():
        handler = MessageHandler(
            Mock(name='message'), Mock(name='queue'),
            Mock(name='event_captor'))
        handler._payload = {'guid': 42}  # noqa: protected-access
        with patch.object(
                MessageHandler, '_serializer_class', RegularModelSerializer):
            assert isinstance(handler._instance, RegularModel)  # noqa: protected-access
            assert handler._instance.uid == 42  # noqa: protected-access
            assert handler._instance._state.adding  # noqa: protected-access

    @staticmethod
    def test_queryset():
        handler = MessageHandler(
            Mock(name='message'), Mock(name='queue'),
            Mock(name='event_captor'))
        with patch.object(
                MessageHandler, '_serializer_class', RegularModelSerializer):
            assert isinstance(handler._queryset, Manager)  # noqa: protected-access

    @staticmethod
    def test_model():
        handler = MessageHandler(
            Mock(name='message'), Mock(name='queue'),
            Mock(name='event_captor'))
        with patch.object(
                MessageHandler, '_serializer_class', RegularModelSerializer):
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
                MessageHandler, '_serializer_class', RegularModelSerializer):
                    handler._update_instance()  # noqa: protected-access

        assert list(RegularModel.objects.values('name', 'uid')) == [{
            'uid': UUID('b24d988e-42aa-477d-a8c3-a88b127b9b31'),
            'name': 'Test'
        }]

    @staticmethod
    @pytest.mark.django_db
    @patch.object(
        MessageHandler, '_serializer_class',
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
        MessageHandler, '_serializer_class',
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
    @patch.object(MessageHandler, '_serializer_class', RegularModelSerializer)
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
    @patch('pik.bus.consumer.MessageHandler._get_serializer', Mock())
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
    @patch('pik.bus.consumer.MessageHandler._get_serializer', Mock())
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
    @patch('pik.bus.consumer.MessageHandler._get_serializer', Mock())
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

# TODO:
# Сделать тесты:
# 1. Удаление ошибки после успеха
# 2. Ошибка валидации уже была но приехала еще новая валидация
# 3. Системная Ошибка уже была но приехала еще новая системная
# 4. Ошибка валидации уже была но приехала еще новая системная
# 5. Системная Ошибка уже была но приехала еще новая валидация
# Тесты на проверку того что уже есть 2 сообщение в базе
# 7. Системная ошибка если она уже была,
#   а была еще валидация PIKMessage(body_hash) PIKMessage(entity_uid)
# 8. Ошибка валидации если она уже была,
#   а была еще системная PIKMessage(body_hash) PIKMessage(entity_uid)
