import contextlib
import io
import logging
from functools import partial
from hashlib import sha1
from itertools import chain
from typing import Set
from uuid import UUID

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from pika import BlockingConnection, URLParameters
from pika.exceptions import (
    AMQPConnectionError, ChannelWrongStateError, ChannelClosedByBroker,
    ChannelClosed)
from rest_framework.parsers import JSONParser
from rest_framework.exceptions import ValidationError
from tenacity import retry, retry_if_exception_type, wait_fixed

from pik.api.exceptions import (
    extract_exception_data, NewestUpdateValidationError)
from pik.bus.mdm import mdm_event_captor
from pik.bus.models import PIKMessageException
from pik.utils.bus import LiveBlockingConnection
from pik.utils.case_utils import underscorize
from pik.utils.sentry import capture_exception
from pik.bus.exceptions import QueuesMissingError, SerializerMissingError


logger = logging.getLogger(__name__)


class MessageHandler:
    LOCK_TIMEOUT = 60
    parser_class = JSONParser

    _body = None
    _queue = None
    _event_captor = None

    _payload = None
    _parsed_payload = None
    _serializers = None
    _event_label = 'deserialization'

    def __init__(self, body, queue, event_captor):
        self._body = body
        self._queue = queue
        self._event_captor = event_captor

    def handle(self):
        try:
            self._fetch_payload()
            self._prepare_payload()
            self._update_instance()
            self._process_dependants()
            self._register_success()
            return True
        except Exception as error:  # noqa: too-broad-except
            self._register_error(error)
            return False

    def _register_success(self):
        for msg in self._error_messages:
            msg.delete()
        self._capture_event(success=True, error=None)

    def _register_error(self, error):
        self._capture_event(success=False, error=error)
        self._capture_exception(error)

    @property
    def _error_messages(self):
        error_messages = PIKMessageException.objects.filter(
            queue=self._queue, body_hash=self._body_hash).order_by(
            '-updated')
        if self._entity_uid:
            error_messages = (
                entity for entity in sorted(chain(
                    error_messages,
                    PIKMessageException.objects.filter(
                        queue=self._queue, entity_uid=self._entity_uid
                    ).order_by('-updated')), key=lambda x: -x.updated))
        return error_messages

    @cached_property
    def envelope(self):
        return self.parser_class().parse(io.BytesIO(self._body))

    @classmethod
    def get_queue_serializers(cls) -> dict:
        return {
            queue: import_string(serializer)
            for queue, serializer in settings.RABBITMQ_CONSUMES.items()}

    def _fetch_payload(self):
        self._payload = self.envelope['message']

    def _prepare_payload(self):
        self._payload = underscorize(self._payload)

        if hasattr(self._serializer_class, 'underscorize_hook'):
            self._payload = self._serializer_class.underscorize_hook(
                self._payload)

    def _update_instance(self):
        guid = self._payload.get('guid')
        queue = self._queue
        lock = (
            cache.lock(f'bus-{queue}-{guid}', timeout=self.LOCK_TIMEOUT)
            if guid else contextlib.nullcontext())
        with lock:
            try:
                self._serializer.is_valid(raise_exception=True)
            except ValidationError as exc:
                if NewestUpdateValidationError.is_error_match(exc):
                    capture_exception(exc)
                    return
                raise
            self._serializer.save()

    @cached_property
    def _serializer(self):
        return self._serializer_class(self._instance, self._payload)

    @cached_property
    def _entity_uid(self):
        try:
            return str(UUID(self._payload.get('guid')))
        except Exception as error:  # noqa: broad-except
            capture_exception(error)
            return None

    @cached_property
    def _body_hash(self):
        return sha1(self._body).hexdigest()

    @cached_property
    def _instance(self):
        try:
            return self._queryset.get(uid=self._entity_uid)
        except self._model.DoesNotExist:
            return self._model(uid=self._payload['guid'])

    @property
    def _model(self):
        return self._serializer_class.Meta.model

    @property
    def _queryset(self):
        return getattr(self._model, 'all_objects', self._model.objects)

    @property
    def _serializer_class(self):
        return self._get_serializer(self._queue)

    @classmethod
    def _get_serializer(cls, queue):
        """
            Queue name to serializer mapping dict `{queue:  serializer, ... }`

            We want to build it once and use forever, but building it on
                startup is redundant for other workers and tests
        """
        if cls._serializers is None:
            cls._serializers = cls.get_queue_serializers()
        if not cls._serializers or queue not in cls._serializers:  # noqa: unsupported-membership-test
            raise SerializerMissingError(
                f'Unable to find serializer for {queue}')
        return cls._serializers[queue]  # noqa: unsupported-membership-test

    def _process_dependants(self):
        from .models import PIKMessageException  # noqa: cyclic import workaround
        dependants = PIKMessageException.objects.filter(
            dependencies__contains={
                self._payload["type"]: self._entity_uid})
        for dependant in dependants:
            handler = self.__class__(
                dependant.message, dependant.queue, mdm_event_captor)
            if handler.handle():
                dependant.delete()

    def _capture_exception(self, exc):
        # Don't spam validation errors to sentry.
        if not isinstance(exc, ValidationError):
            capture_exception(exc)

        exc_data = extract_exception_data(exc)

        errors_messages = self._error_messages
        if not errors_messages:
            errors_messages = [PIKMessageException(
                entity_uid=self._entity_uid,
                body_hash=self._body_hash,
                queue=self._queue)]

        err_msg, other_errors = errors_messages[0], errors_messages[1:]
        err_msg.message = self._body
        err_msg.exception = exc_data
        err_msg.exception_type = exc_data['code']
        err_msg.exception_message = exc_data['message']

        is_missing_dependency = ('does_not_exist' in [
            detail[0]['code']
            for detail in exc_data.get('detail', {}).values()])
        if is_missing_dependency:
            err_msg.dependencies = {
                self._payload[field]['type']: self._payload[field]['guid']
                for field, errors in exc_data.get('detail', {}).items()
                for error in errors
                if error['code'] == 'does_not_exist'}

        for _err_msg in other_errors:
            _err_msg.delete()

        err_msg.save()

    def _capture_event(self, **kwargs):
        self._event_captor.capture(
            event=self._event_label,
            entity_type=self.envelope.get('message', {}).get('type'),
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
                retry_state.attempt_number)
    )
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
        else:
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
