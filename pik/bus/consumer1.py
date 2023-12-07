import contextlib
import io
import logging
from hashlib import sha1
from typing import Dict, Type
from uuid import UUID

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser
from rest_framework.serializers import Serializer

from pik.api.exceptions import (
    extract_exception_data, NewestUpdateValidationError)
from pik.bus.exceptions import SerializerMissingError
from pik.bus.mdm import mdm_event_captor
from pik.bus.models import PIKMessageException
from pik.utils.case_utils import underscorize
from pik.utils.decorators import close_old_db_connections
from pik.utils.sentry import capture_exception


logger = logging.getLogger(__name__)


class MessageHandler:
    parser_class = JSONParser

    LOCK_TIMEOUT = 60
    OBJECT_UNCHANGED_MESSAGE = 'Object unchanged.'

    _body: bytes = b''
    _queue: str = ''

    _payload = None
    _queue_serializers_cache: Dict[str, Type[Serializer]] = {}
    _event_label = 'deserialization'

    def __init__(self, body: bytes, queue: str):
        self._body = body
        self._queue = queue

    @close_old_db_connections
    def handle(self):
        try:
            # TODO: separate class to MessageHandler and ErrorHandler.
            # TODO: union _fetch_payload and _prepare_payload to _payload
            #  property.
            self._fetch_payload()
            self._prepare_payload()
            self._update_instance()
            # self._process_dependants()
            # self._register_success()
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
        print('_update_instance')
        # # TODO: remove `contextlib.nullcontext()`, guid must be only UUID.
        # lock = (
        #     cache.lock(
        #         f'bus-{self._queue}-{self._uid}', timeout=self.LOCK_TIMEOUT)
        #     if self._uid else contextlib.nullcontext())
        # # TODO: move context manager to class decorator for reuse.
        # with lock:
        #     self._serializer.is_valid(raise_exception=True)
        #     self._serializer.save()

    @cached_property
    def _uid(self):
        # TODO: remove try-except, guid must be only UUID.
        try:
            guid = self._payload.get('guid')
            UUID(guid)  # For validation.
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
                dependant.message, dependant.queue)
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
        error_message.message = self._body
        error_message.exception = exc_data
        error_message.exception_type = exc_data['code']
        error_message.exception_message = exc_data['message']

        is_missing_dependency = ('does_not_exist' in [
            detail[0]['code']
            for detail in exc_data.get('detail', {}).values()])
        if is_missing_dependency:
            error_message.dependencies = {
                self._payload[field]['type']: self._payload[field]['guid']
                for field, errors in exc_data.get('detail', {}).items()
                for error in errors if error['code'] == 'does_not_exist'}

        for same_error_message in same_error_messages:
            same_error_message.delete()

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
        ddd = {
                'event': event,
                'entity_type': self.envelope.get('message', {}).get('type'),
                'entity_guid': self.envelope.get('message', {}).get('guid'),
                'transactionGUID':  self.envelope.get('headers', {}).get('transactionGUID'),
                'transactionMessageCount':  self.envelope.get('headers', {}).get('transactionMessageCount'),
                **kwargs}
        print()

