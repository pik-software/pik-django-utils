import json
from unittest.mock import Mock, patch, call
from uuid import UUID

import pytest
from django.db.models import QuerySet, Manager
from rest_framework.exceptions import ParseError, ValidationError, ErrorDetail
from rest_framework.fields import UUIDField, DateTimeField
from rest_framework.serializers import ModelSerializer, CharField

from pik.api.serializers import StandardizedModelSerializer
from pik.bus.consumer import MessageConsumer, MessageHandler, \
    QueueSerializerMissingExcpetion
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
    def test_ok(self):
        handler = MessageHandler(b'{"message": {}}', Mock(name='queue'))
        handler._fetch_payload()
        assert handler._payload == {}

    def test__not_json(self):
        handler = MessageHandler(b'', Mock(name='queue'))
        with pytest.raises(ParseError):
            handler._fetch_payload()
        assert handler._payload is None

    def test_message_missing(self):
        handler = MessageHandler(b'{}', Mock(name='queue'))
        with pytest.raises(KeyError):
            handler._fetch_payload()
        assert handler._payload is None

    def test_not_bytes(self):
        handler = MessageHandler(42, Mock(name='queue'))
        with pytest.raises(TypeError):
            handler._fetch_payload()
        assert handler._payload is None


class TestMessageHandlerPrepare:
    def test_ok(self):
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        handler._payload = {'someValue': 42}
        with patch.object(
                MessageHandler, '_serializer_class',
                Mock(underscorize_hook=Mock(side_effect=lambda x: x))
                ) as serializer:
            handler._prepare_payload()
        assert handler._payload == {'some_value': 42}
        assert serializer.underscorize_hook.called

    def test_serializer_missing(self):
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        handler._payload = {'someValue': 42}
        handler._serializers = {}
        with pytest.raises(QueueSerializerMissingExcpetion):
            handler._prepare_payload()
        assert handler._payload == {'some_value': 42}

    def test_invalid_payload(self):
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        payload = Exception()
        handler._payload = payload
        with patch.object(
                MessageHandler, '_serializer_class',
                Mock(underscorize_hook=Mock(side_effect=lambda x: x))):
            handler._prepare_payload()
        assert handler._payload == payload


class TestMessageHandlerUpdateInstance:
    @pytest.mark.django_db
    def test_instance_exists(self):
        RegularModel(
            uid=UUID('b24d988e-42aa-477d-a8c3-a88b127b9b31'),
            name='Existing').save()
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        handler._payload = {'guid': 'b24d988e-42aa-477d-a8c3-a88b127b9b31'}
        with patch.object(MessageHandler, '_serializer_class', RegularModelSerializer):
            assert isinstance(handler._instance, RegularModel)
            assert handler._instance.uid == UUID('b24d988e-42aa-477d-a8c3-a88b127b9b31')
            assert not handler._instance._state.adding

    @pytest.mark.django_db
    def test_instance_missing(self):
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        handler._payload = {'guid': 42}
        with patch.object(
                MessageHandler, '_serializer_class', RegularModelSerializer):
            assert isinstance(handler._instance, RegularModel)
            assert handler._instance.uid == 42
            assert handler._instance._state.adding

    def test_queryset(self):
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        with patch.object(
                MessageHandler, '_serializer_class', RegularModelSerializer):
            assert isinstance(handler._queryset, Manager)

    def test_model(self):
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        with patch.object(
                MessageHandler, '_serializer_class', RegularModelSerializer):
            assert handler._model == RegularModel

    @pytest.mark.django_db
    def test_ok(self):
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        handler._payload = {
            'guid': 'b24d988e-42aa-477d-a8c3-a88b127b9b31', 'name': 'Test'}
        with patch.object(
                MessageHandler, '_serializer_class', RegularModelSerializer):
                    handler._update_instance()

        assert list(RegularModel.objects.values('name', 'uid')) == [{
            'uid': UUID('b24d988e-42aa-477d-a8c3-a88b127b9b31'), 'name': 'Test'
        }]

    @pytest.mark.django_db
    @patch.object(
        MessageHandler, '_serializer_class',
        RemovableRegularDependedSerializer)
    def test_missing_depended_model(self):
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        handler._payload = {
            'guid': 'b24d988e-42aa-477d-a8c3-a88b127b9b31',
            'dependence': {
                'guid': 'b24d988e-42aa-477d-a8c3-a88b127b9b31',
                'type': 'regularmodel'}}

        with patch.object(MessageHandler, '_instance', RemovableRegularDepended()):
            with pytest.raises(ValidationError) as exc:
                handler._update_instance()
            assert exc.value.detail == {'dependence': [
                ErrorDetail(
                    string=('Недопустимый guid '
                            '"b24d988e-42aa-477d-a8c3-a88b127b9b31" - '
                            'объект не существует.'),
                    code='does_not_exist')]}

    @pytest.mark.django_db
    @patch.object(
        MessageHandler, '_serializer_class',
        RemovableRegularDependedSerializer)
    def test_multiple_error_model(self):
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        handler._payload = {
            'guid': 'b24d988e-42aa-477d-a8c3-a88b127b9b31',
            'created': 'zzzz',
            'dependence': {
                'guid': 'b24d988e-42aa-477d-a8c3-a88b127b9b31',
                'type': 'regularmodel'}}

        with patch.object(MessageHandler, '_instance', RemovableRegularDepended()):
            with pytest.raises(ValidationError) as exc:
                handler._update_instance()
            assert exc.value.detail == {'created': [ErrorDetail(
                string=(
                    'Datetime has wrong format. Use one of these formats '
                    'instead: '
                    'YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].'),
                code='invalid')], 'dependence': [ErrorDetail(
                string='Недопустимый guid "b24d988e-42aa-477d-a8c3-a88b127b9b31" - объект не существует.',
                code='does_not_exist')]}


@pytest.mark.django_db
class TestMessageHandlerException:
    def test_unexpected_error(self):
        PIKMessageException(
            uid='dbef014c-1ece-f8f9-9e5e-fa78cf01680d',
            exception='', queue='test_queue').save()
        handler = MessageHandler(b'test_message', 'test_queue')
        handler._capture_exception(Exception('test'))
        assert list(PIKMessageException.objects.values(
            'queue', 'message', 'exception', 'exception_type',
            'exception_message', 'uid')) == [
                   {'exception': {'code': 'Exception',
                                  'message': 'test'},
                    'uid': UUID('dbef014c-1ece-f8f9-9e5e-fa78cf01680d'),
                    'exception_message': 'test',
                    'exception_type': 'Exception',
                    'message': b'test_message',
                    'queue': 'test_queue'}]

    def test_validation_error(self):
        PIKMessageException(
            uid='dbef014c-1ece-f8f9-9e5e-fa78cf01680d',
            entity_uid='dbef014c-1ece-f8f9-9e5e-fa78cf01680d',
            exception='', queue='test_queue').save()
        handler = MessageHandler(b'test_message', 'test_queue')
        handler._payload = {'guid': 'dbef014c-1ece-f8f9-9e5e-fa78cf01680d'}
        handler._capture_exception(ValidationError({'name': [
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

    def test_dependency_error(self):
        PIKMessageException(
            uid='dbef014c-1ece-f8f9-9e5e-fa78cf01680d',
            entity_uid='dbef014c-1ece-f8f9-9e5e-fa78cf01680d',
            exception='', queue='test_queue').save()
        handler = MessageHandler(b'test_message', 'test_queue')
        handler._payload = {
            'guid': 'dbef014c-1ece-f8f9-9e5e-fa78cf01680d',
            'dependence': {'guid': 'DependencyGuid', 'type': 'DependencyType'}}
        handler._capture_exception(ValidationError({'created': [
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
            'exception': {'code': 'invalid',
                          'detail': {'created': [{
                              'code': 'invalid',
                              'message': 'Datetime has wrong format. '
                                         'Use one of these formats '
                                         'instead: '
                                         'YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].'}],
                              'dependence': [{
                                  'code': 'does_not_exist',
                                  'message': 'Недопустимый guid '
                                             '"b24d988e-42aa-477d-a8c3-a88b127b9b31" '
                                             '- объект не '
                                             'существует.'}]},
                          'message': 'Invalid input.'},
            'exception_message': 'Invalid input.',
            'exception_type': 'invalid',
            'message': b'test_message',
            'queue': 'test_queue'}]


@pytest.mark.django_db
class TestMessageHandlerDependencies:
    def test_missing_dependency(self):
        handler = MessageHandler(Mock(name='message'), Mock(name='queue'))
        handler._payload = {'guid': 42, 'type': 'RegularModel'}
        handler._process_dependants()

    @patch.object(MessageHandler, '_serializer_class', RegularModelSerializer)
    def test_process_dependency(self):
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
        handler._payload = {'guid': 42, 'type': 'DependantModel'}
        handler._process_dependants()

        assert list(RegularModel.objects.values('uid', 'name')) == [{
            'uid': UUID('00000000-0000-0000-0000-000000000000'),
            'name': 'Dependency'}]

        assert PIKMessageException.objects.count() == 0
