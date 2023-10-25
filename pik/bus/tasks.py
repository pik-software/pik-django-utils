import logging

from django.conf import settings
from django.utils.module_loading import import_string
from celery import app

from pik.utils.sentry import capture_exception
from pik.modeladmin.tasks import PIKProgressor

from .mdm import mdm_event_captor
from .models import PIKMessageException


logger = logging.getLogger(__name__)
handler_class = import_string(getattr(
    settings, 'RABBITMQ_MESSAGE_HANDLER_CLASS',
    'pik.bus.consumer.MessageHandler'))


@app.shared_task(bind=True)
def task_process_messages(self, progress_id, pks, *args, **kwargs):
    progress = PIKProgressor(progress_id)
    queryset = PIKMessageException.objects.filter(
        pk__in=pks).order_by('updated')

    try:
        for obj in queryset:
            handler = handler_class(obj.message, obj.queue, mdm_event_captor)
            success = handler.handle()
            progress.apply_item_status(success)
    except Exception as exc:  # noqa: broad-except
        capture_exception(exc)
        progress.set_values(error=f'{exc.__class__.__name__}: {str(exc)}')


@app.shared_task(bind=True)
def task_delete_messages(self, progress_id, pks, *args, **kwargs):
    progres = PIKProgressor(progress_id)
    queryset = PIKMessageException.objects.filter(pk__in=pks)

    try:
        for obj in queryset:
            success = True
            try:
                obj.delete()
            except Exception as exc:  # noqa: broad-except
                success = False
            progres.apply_item_status(success)
    except Exception as exc:  # noqa: broad-except
        capture_exception(exc)
        progres.set_values(error=f'{exc.__class__.__name__}: {str(exc)}')
