from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from pik.utils.sentry import capture_exception
from pik.bus.producer import (
    InstanceHandler, message_producer, ResponseCommandInstanceHandler)
from pik.bus.mdm import mdm_event_captor


def ignore_if_migrate(func):
    def wrapper(instance, **kwargs):
        # Ignoring migration signals.
        if instance.__module__ == '__fake__':
            return
        func(instance, **kwargs)
    return wrapper


@receiver(post_save)
@ignore_if_migrate
def produce_entity(instance, **kwargs):
    if not settings.RABBITMQ_PRODUCER_ENABLE:
        return
    try:
        InstanceHandler(instance, mdm_event_captor, message_producer).handle()
    except Exception as exc:  # noqa: broad-except
        capture_exception(exc)


produces_settings4response_command = (
    ResponseCommandInstanceHandler.get_produce_settings())


@receiver(post_save)
@ignore_if_migrate
def produce_command_response(instance, **kwargs):
    if not settings.RABBITMQ_RESPONSER_ENABLE:
        return
    # Ignoring not response command messages.
    # We dn`t generate senders from produces_settings4response_command to
    # create decorators because is unnecessary complication.
    if instance.__class__.__name__ not in produces_settings4response_command:
        return
    try:
        response = instance
        routing_key = response.request.requesting_service
        ResponseCommandInstanceHandler(
            instance, mdm_event_captor, message_producer, routing_key).handle()
    except Exception as exc:  # noqa: broad-except
        capture_exception(exc)
