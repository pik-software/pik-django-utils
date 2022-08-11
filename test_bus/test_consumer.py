import json
from unittest.mock import Mock, patch
from uuid import UUID

import pytest
from django.db.models import Manager
from rest_framework.exceptions import ParseError, ValidationError, ErrorDetail
from rest_framework.fields import DateTimeField
from rest_framework.serializers import CharField

from pik.api.serializers import StandardizedModelSerializer
from pik.bus.consumer import (MessageHandler, QueueSerializerMissingExcpetion)
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
        handler = MessageHandler(b'{"message": {}}', Mock(name='queue'))
        handler._fetch_payload()  # noqa: protected-access
        assert handler._payload == {}  # noqa: protected-access

    @staticmethod
    def test__not_json():
        handler = MessageHandler(b'', Mock(name='queue'))
        with pytest.raises(ParseError):
            handler._fetch_payload()  # noqa: protected-access
        assert handler._payload is None  # noqa: protected-access

    @staticmethod
    def test_message_missing():
        handler = MessageHandler(b'{}', Mock(name='queue'))
        with pytest.raises(KeyError):
            handler._fetch_payload()  # noqa: protected-access
        assert handler._payload is None  # noqa: protected-access

    @staticmethod
    def test_not_bytes():
        handler = MessageHandler(42, Mock(name='queue'))
        with pytest.raises(TypeError):
            handler._fetch_payload()  # noqa: protected-access
        assert handler._payload is None  # noqa: protected-access


class TestMessageHandlerPrepare:
    @staticmethod
    def test_ok():
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        handler._payload = {'someValue': 42}  # noqa: protected-access
        with patch.object(MessageHandler, '_serializer_class', Mock(
                underscorize_hook=Mock(
                    side_effect=lambda x: x))) as serializer:
            handler._prepare_payload()  # noqa: protected-access
        assert handler._payload == {'some_value': 42}  # noqa: protected-access
        assert serializer.underscorize_hook.called

    @staticmethod
    def test_serializer_missing():
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        handler._payload = {'someValue': 42}  # noqa: protected-access
        handler._serializers = {}  # noqa: protected-access
        with pytest.raises(QueueSerializerMissingExcpetion):
            handler._prepare_payload()  # noqa: protected-access
        assert handler._payload == {'some_value': 42}  # noqa: protected-access

    @staticmethod
    def test_invalid_payload():
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
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
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
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
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        handler._payload = {'guid': 42}  # noqa: protected-access
        with patch.object(
                MessageHandler, '_serializer_class', RegularModelSerializer):
            assert isinstance(handler._instance, RegularModel)  # noqa: protected-access
            assert handler._instance.uid == 42  # noqa: protected-access
            assert handler._instance._state.adding  # noqa: protected-access

    @staticmethod
    def test_queryset():
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        with patch.object(
                MessageHandler, '_serializer_class', RegularModelSerializer):
            assert isinstance(handler._queryset, Manager)  # noqa: protected-access

    @staticmethod
    def test_model():
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        with patch.object(
                MessageHandler, '_serializer_class', RegularModelSerializer):
            assert handler._model == RegularModel  # noqa: protected-access

    @staticmethod
    @pytest.mark.django_db
    def test_ok():
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        handler._payload = {  # noqa: protected-access
            'guid': 'b24d988e-42aa-477d-a8c3-a88b127b9b31', 'name': 'Test'}
        with patch.object(
                MessageHandler, '_serializer_class', RegularModelSerializer):
                    handler._update_instance()  # noqa: protected-access

        assert list(RegularModel.objects.values('name', 'uid')) == [{
            'uid': UUID('b24d988e-42aa-477d-a8c3-a88b127b9b31'), 'name': 'Test'
        }]

    @staticmethod
    @pytest.mark.django_db
    @patch.object(
        MessageHandler, '_serializer_class',
        RemovableRegularDependedSerializer)
    def test_missing_depended_model():
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
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
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
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
            exception='', queue='test_queue').save()
        handler = MessageHandler(b'test_message', 'test_queue')
        handler._capture_exception(Exception('test'))  # noqa: protected-access
        assert list(PIKMessageException.objects.values(
            'queue', 'message', 'exception', 'exception_type',
            'exception_message', 'uid')) == [{
                'exception': {'code': 'Exception', 'message': 'test'},
                'uid': UUID('dbef014c-1ece-f8f9-9e5e-fa78cf01680d'),
                'exception_message': 'test',
                'exception_type': 'Exception',
                'message': b'test_message',
                'queue': 'test_queue'}]

    @staticmethod
    def test_validation_error():
        PIKMessageException(
            uid='dbef014c-1ece-f8f9-9e5e-fa78cf01680d',
            entity_uid='dbef014c-1ece-f8f9-9e5e-fa78cf01680d',
            exception='', queue='test_queue').save()
        handler = MessageHandler(b'test_message', 'test_queue')
        handler._payload = {'guid': 'dbef014c-1ece-f8f9-9e5e-fa78cf01680d'}  # noqa: protected-access
        handler._capture_exception(ValidationError({'name': [  # noqa: protected-access
            ErrorDetail(string='This field is required.', code='required')]}))
        assert list(PIKMessageException.objects.values(
            'queue', 'message', 'exception', 'exception_type',
            'exception_message')) == [{
                'exception': {'code': 'invalid',
                              'detail': {'name': [{
                                  'code': 'required',
                                  'message': 'This field is required.'}]},
                              'message': 'Invalid input.'},
                'exception_message': 'Invalid input.',
                'exception_type': 'invalid',
                'message': b'test_message',
                'queue': 'test_queue'}]

    @staticmethod
    def test_dependency_error():
        PIKMessageException(
            uid='dbef014c-1ece-f8f9-9e5e-fa78cf01680d',
            entity_uid='dbef014c-1ece-f8f9-9e5e-fa78cf01680d',
            exception='', queue='test_queue').save()
        handler = MessageHandler(b'test_message', 'test_queue')
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
        assert list(PIKMessageException.objects.values(
            'queue', 'message', 'exception', 'exception_type',
            'exception_message', 'dependencies')) == [{
                'dependencies': {'DependencyType': 'DependencyGuid'},
                'exception': {
                    'code': 'invalid',
                    'detail': {
                        'created': [{
                            'code': 'invalid',
                            'message': (
                                'Datetime has wrong format. Use one of these '
                                'formats instead: YYYY-MM-DDThh:mm'
                                '[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].')}],
                        'dependence': [{
                            'code': 'does_not_exist',
                            'message': (
                                'Недопустимый guid '
                                '"b24d988e-42aa-477d-a8c3-a88b127b9b31" '
                                '- объект не существует.')}]},
                    'message': 'Invalid input.'},
                'exception_message': 'Invalid input.',
                'exception_type': 'invalid',
                'message': b'test_message',
                'queue': 'test_queue'}]


@pytest.mark.django_db
class TestMessageHandlerDependencies:
    @staticmethod
    def test_missing_dependency():
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        handler._payload = {'guid': 42, 'type': 'RegularModel'}  # noqa: protected-access
        handler._process_dependants()  # noqa: protected-access

    @staticmethod
    @patch.object(MessageHandler, '_serializer_class', RegularModelSerializer)
    def test_process_dependency():
        PIKMessageException(
            message=json.dumps({'message': {
                'type': 'Dependency',
                'name': 'Dependency',
                'guid': '00000000-0000-0000-0000-000000000000'
            }}).encode('utf8'),
            exception='',

            queue='test_queue',
            dependencies={'DependantModel': 42}).save()

        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        handler._payload = {'guid': 42, 'type': 'DependantModel'}  # noqa: protected-access
        handler._process_dependants()  # noqa: protected-access

        assert list(RegularModel.objects.values('uid', 'name')) == [{
            'uid': UUID('00000000-0000-0000-0000-000000000000'),
            'name': 'Dependency'}]

        assert PIKMessageException.objects.count() == 0
