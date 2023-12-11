import contextlib
import io
import logging
from functools import partial
from hashlib import sha1
from typing import Set, Dict, Type
import uuid

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from pika import BlockingConnection, URLParameters
from pika.exceptions import (
    AMQPConnectionError, ChannelWrongStateError, ChannelClosedByBroker,
    ChannelClosed)
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser
from rest_framework.serializers import Serializer
from tenacity import retry, retry_if_exception_type, wait_fixed

from pik.api.exceptions import (
    extract_exception_data, NewestUpdateValidationError)
from pik.bus.exceptions import QueuesMissingError, SerializerMissingError
from pik.bus.mdm import mdm_event_captor
from pik.bus.models import PIKMessageException
from pik.utils.bus import LiveBlockingConnection
from pik.utils.case_utils import underscorize
from pik.utils.decorators import close_old_db_connections
from pik.utils.sentry import capture_exception
from pik.bus.choices import REQUEST_COMMAND_STATUS_CHOICES


logger = logging.getLogger(__name__)


class CommandError(Exception):
    pass


class MessageHandler:
    parser_class = JSONParser

    LOCK_TIMEOUT = 60
    OBJECT_UNCHANGED_MESSAGE = 'Object unchanged.'

    _body: bytes = b''
    _queue: str = ''
    _event_captor: object = None

    _payload = None
    _queue_serializers_cache: Dict[str, Type[Serializer]] = {}
    _event_label = 'deserialization'

    def __init__(self, body: bytes, queue: str, event_captor: object):
        self._body = body
        self._queue = queue
        self._event_captor = event_captor

    @close_old_db_connections
    def handle(self):
        try:
            # TODO: separate class to MessageHandler and ErrorHandler.
            # TODO: union _fetch_payload and _prepare_payload to _payload?
            self._fetch_payload()
            self._prepare_payload()
            self._update_instance()
            self._process_dependants()
            self._register_success()
            return True
        except Exception as error:  # noqa: too-broad-except
            self._register_error(error)
            return False

    def _fetch_payload(self):
        self._payload = self.envelope['message']

    @cached_property
    def envelope(self):
        return self.parser_class().parse(io.BytesIO(self._body))

    def _prepare_payload(self):
        self._payload = underscorize(self._payload)

        if hasattr(self._serializer_cls, 'underscorize_hook'):
            self._payload = self._serializer_cls.underscorize_hook(
                self._payload)

    def _update_instance(self):
        # TODO: remove `contextlib.nullcontext()`, guid must be only UUID.
        lock = (
            cache.lock(
                f'bus-{self._queue}-{self._uid}', timeout=self.LOCK_TIMEOUT)
            if self._uid else contextlib.nullcontext())
        # TODO: move context manager to class decorator for reuse.
        with lock:
            self._serializer.is_valid(raise_exception=True)
            self._serializer.save()

    @cached_property
    def _uid(self):
        # TODO: remove try-except, guid must be only UUID.
        try:
            guid = self._payload.get('guid')
            uuid.UUID(guid)  # For validation.
            return guid
        except Exception as error:  # noqa: broad-except
            capture_exception(error)
            return None

    @cached_property
    def _serializer(self):
        return self._serializer_cls(self._instance, self._payload)

    @property
    def _serializer_cls(self) -> Type[Serializer]:
        if self._queue not in self.queue_serializers:  # noqa: unsupported-membership-test
            raise SerializerMissingError(
                f'Unable to find serializer for `{self._queue}`')
        return self.queue_serializers[self._queue]  # noqa: unsupported-membership-test

    @property
    def queue_serializers(self) -> Dict[str, Type[Serializer]]:
        """
        Caching _queue_serializers property and return it.
        We want to build it once and use forever, but building it on startup is
        redundant for other workers and tests.
        """

        if not self._queue_serializers_cache:
            self._queue_serializers_cache.update(self._queue_serializers)
        return self._queue_serializers_cache

    @property
    def _queue_serializers(self) -> Dict[str, Type[Serializer]]:
        """
        Example of return value:
        ```{
            'queue': serializer_cls,
            ...
        }```
        """

        return {
            queue: import_string(serializer)
            for queue, serializer in self.consumes_setting.items()}

    @property
    def consumes_setting(self):
        return settings.RABBITMQ_CONSUMES

    @cached_property
    def _instance(self):
        try:
            # TODO: self._uid can be None, it`s wrong.
            return self._queryset.get(uid=self._uid)
        except self._model.DoesNotExist:
            return self._model(uid=self._uid)

    @cached_property
    def _queryset(self):
        return getattr(self._model, 'all_objects', self._model.objects)

    @cached_property
    def _model(self):
        # More easy way is get model from instance? No, we get cyclic call.
        return self._serializer_cls.Meta.model

    def _process_dependants(self):
        from .models import PIKMessageException  # noqa: cyclic import workaround
        dependants = PIKMessageException.objects.filter(
            dependencies__contains={
                self._payload['type']: self._uid})
        for dependant in dependants:
            handler = self.__class__(
                dependant.message, dependant.queue, mdm_event_captor)
            if handler.handle():
                dependant.delete()

    def _register_success(self):
        for msg in self._error_messages:
            msg.delete()
        self._capture_event(success=True, error=None)

    @cached_property
    def _body_hash(self):
        return sha1(self._body).hexdigest()

    def _register_error(self, error):
        if not NewestUpdateValidationError.is_error_match(error):
            self._capture_event(success=False, error=error)
        self._capture_exception(error)

    def _capture_exception(self, exc):
        # Don't spam validation errors to sentry.
        if not isinstance(exc, ValidationError):
            capture_exception(exc)

        # Don't capture race errors for consumer.
        if NewestUpdateValidationError.is_error_match(exc):
            self._capture_event(
                event='skip', success=True,
                error=self.OBJECT_UNCHANGED_MESSAGE)
            capture_exception(exc)
            return

        exc_data = extract_exception_data(exc)

        error_messages = self._error_messages
        if not error_messages:
            error_messages = [
                PIKMessageException(
                    entity_uid=self._uid,
                    body_hash=self._body_hash,
                    queue=self._queue)]

        error_message, *same_error_messages = error_messages
        for same_error_message in same_error_messages:
            same_error_message.delete()

        error_message.message = self._body
        error_message.exception = exc_data
        error_message.exception_type = exc_data['code']
        error_message.exception_message = exc_data['message']

        is_missing_dependency = ('does_not_exist' in [
            detail[0]['code']
            for detail in exc_data.get('detail', {}).values()])
        if is_missing_dependency:
            error_message.dependencies = {
                self._payload[field]['type']:
                    self._payload[field]['guid'].lower()
                for field, errors in exc_data.get('detail', {}).items()
                for error in errors if error['code'] == 'does_not_exist'}

        error_message.save()

    @property
    def _error_messages(self):
        lookups = Q(queue=self._queue) & Q(body_hash=self._body_hash)
        if self._uid:
            lookups = (
                Q(queue=self._queue) &
                (Q(body_hash=self._body_hash) |
                 Q(entity_uid=self._uid)))
        return (
            PIKMessageException.objects.filter(lookups).order_by('-updated'))

    def _capture_event(self, event=None, **kwargs):
        if not event:
            event = self._event_label
        self._event_captor.capture(
            event=event,
            entity_type=self.envelope.get('message', {}).get('type'),
            # TODO: use self._uid property.
            entity_guid=self.envelope.get('message', {}).get('guid'),
            transactionGUID=self.envelope.get(
                'headers', {}).get('transactionGUID'),
            transactionMessageCount=self.envelope.get(
                'headers', {}).get('transactionMessageCount'),
            **kwargs)


class MessageConsumer:
    RECONNECT_WAIT = 1
    PREFETCH_COUNT = 1

    _connection_url = None
    _consumer_name = None
    _queues = None
    _event_captor = None
    _message_handler = None

    _connection = None
    _channel = None

    def __init__(  # noqa: pylint - too-many-arguments
            self, connection_url, consumer_name,
            queues, event_captor, message_handler=MessageHandler):
        self._connection_url = connection_url
        self._consumer_name = consumer_name
        self._queues = queues
        self._event_captor = event_captor
        self._message_handler = message_handler

    def consume(self):
        try:
            self._consume()
        except Exception as error:  # noqa: too-broad-except
            capture_exception(error)

    @retry(
        wait=wait_fixed(RECONNECT_WAIT),
        retry=retry_if_exception_type(AMQPConnectionError),
        after=lambda retry_state:
            logger.warning(
                'Connecting to RabbitMQ. Attempt number: %s',
                retry_state.attempt_number))
    def _consume(self):
        self._connect()
        self._config_channel()
        self._bind_queues()
        self._channel.start_consuming()

    def _connect(self):
        self._connection = self._get_connection()
        self._channel = self._connection.channel()

    def _get_connection(self):
        return BlockingConnection(URLParameters(self._connection_url))

    def _config_channel(self):
        self._channel.basic_qos(prefetch_count=self.PREFETCH_COUNT)
        self._channel.confirm_delivery()

    def _bind_queues(self):
        for queue in self._queues:
            self._bind_queue(queue)

    def _bind_queue(self, queue):
        logger.info('Starting %s queue consumer', queue)
        self._channel.basic_consume(
            on_message_callback=partial(self._handle_message, queue=queue),
            queue=queue)
        logger.info('%s queue consumer stared successfully', queue)

    @staticmethod
    def get_handler_kwargs(**kwargs):
        return {**kwargs, 'event_captor': mdm_event_captor}

    def _handle_message(  # noqa: too-many-arguments
            self, channel, method, properties, body,
            queue):
        logger.info(
            'Handling %s bytes message from %s queue', len(body), queue)
        handler = self._message_handler(**self.get_handler_kwargs(
            body=body, queue=queue))

        envelope = {}
        try:
            envelope = handler.envelope
            handler.handle()
        except Exception as error:  # noqa: too-broad-except
            self._capture_event(envelope, success=False, error=error)
            channel.basic_nack(delivery_tag=method.delivery_tag)
            return
        channel.basic_ack(delivery_tag=method.delivery_tag)
        self._capture_event(envelope, success=True, error=None)

    def _capture_event(self, envelope, **kwargs):
        self._event_captor.capture(
            event='consumption',
            entity_type=envelope.get('message', {}).get('type'),
            entity_guid=envelope.get('message', {}).get('guid'),
            transactionGUID=envelope.get('headers', {}).get(
                'transactionGUID'),
            transactionMessageCount=envelope.get(
                'headers', {}).get('transactionMessageCount'),
            **kwargs)


class AllQueueMessageConsumer(MessageConsumer):
    """
    Message consumer that includes queue existence checking before consuming
    and periodical running function that try to add missing queues.
    """

    CALLBACK_WAIT = 300

    _missing_queues: Set[str] = set()
    _existing_queues: Set[str] = set()

    def _get_connection(self):
        return LiveBlockingConnection(
            URLParameters(self._connection_url),
            periodic_callback=self._bind_missing_queues,
            periodic_callback_interval=self.CALLBACK_WAIT)

    def _bind_missing_queues(self):
        logger.info(
            'Trying to consume missing queues: %s', self._missing_queues)
        self._bind_queues(self._missing_queues)

    def _bind_queues(self, queues=None):  # noqa: pylint - arguments-differ
        queues = self._queues if queues is None else queues.copy()
        for queue in queues:
            try:
                with self._temp_channel() as channel:
                    channel.queue_declare(queue, passive=True)
            # TODO: why two exception class?
            except (  # noqa: pylint - invalid-name
                    ChannelWrongStateError,
                    ChannelClosed) as error:
                logger.warning(
                    'Queue %s does`t exist. Exception: %s', queue, error)
                self._missing_queues.add(queue)
            else:
                self._bind_queue(queue)
                self._existing_queues.add(queue)
                try:
                    self._missing_queues.remove(queue)
                except KeyError as error:  # noqa: pylint - invalid-name
                    logger.warning(
                        'Queue %s already removed from self._existing_queues.'
                        ' Exception: %s', queue, error)
        if not self._existing_queues:
            raise QueuesMissingError('Existing queues is`t found.')

    @contextlib.contextmanager
    def _temp_channel(self):
        """
        Context manager that creates a temporary channel and
        closes this one on exit from `with` block.
        Using:
        with self._temp_channel() as channel:
            channel.queue_declare(...)
        """

        _channel = None
        try:
            _channel = self._connection.channel()
            yield _channel
        except ChannelClosedByBroker as error:  # noqa: pylint - invalid-name
            logger.warning(
                'Channel has already been closed by broker. '
                'Exception: %s', error)
        except Exception as error:  # noqa: pylint - broad-except
            capture_exception(error, 'Cannot open temporary channel.')
        finally:
            if _channel is not None:
                _channel.close()


class RequestCommandMessageHandler(MessageHandler):
    """
    Message handler that executes command request.
    """

    DUPLICATE_REQUEST_ERROR = 'Duplicate request guid for command `{}`.'
    STATUSES = REQUEST_COMMAND_STATUS_CHOICES

    _responses_config_cache = {}

    def _update_instance(self):
        super()._update_instance()
        with cache.lock(
                f'bus-{self._queue}-{self._uid}', timeout=self.LOCK_TIMEOUT):
            self._process_command()

    def _process_command(self):
        if self._serializer_cls not in self.responses_config:
            return
        response_serializer_cls, exec_command_function = self.responses_config[
            self._serializer_cls]
        response_model_cls = response_serializer_cls.Meta.model

        self._check_request(response_model_cls)
        self._create_response(response_model_cls)

        exec_command_function(*(self._instance.uid, ))

    def _check_request(self, response_model_cls):
        try:
            response = response_model_cls.objects.get(request=self._instance)
        except ObjectDoesNotExist:
            return
        error = self.DUPLICATE_REQUEST_ERROR.format(self._model.__name__)
        response.error = error
        response.status = self.STATUSES.failed
        response.save()
        raise CommandError(error)

    def _create_response(self, response_model_cls):
        response_model_cls(
            uid=uuid.uuid4(),
            request=self._instance,
            status=self.STATUSES.accepted).save()

    @property
    def responses_config(self):
        if not self._responses_config_cache:
            self._responses_config_cache.update(self._responses_config)
        return self._responses_config_cache

    @property
    def _responses_config(self):
        return {
            import_string(request_cls):
                tuple(map(import_string, config))
            for request_cls, config in self.responses_setting.items()}

    @property
    def responses_setting(self):
        return settings.RABBITMQ_RESPONSES
