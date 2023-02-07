import logging
from datetime import datetime

from django.conf import settings
from django.utils.module_loading import import_string
from celery import app

from pik.utils.sentry import capture_exception
from pik.modeladmin.tasks import register_progress

from .mdm import mdm_event_captor
from .models import PIKMessageException


logger = logging.getLogger(__name__)
handler_class = import_string(getattr(
    settings, 'RABBITMQ_MESSAGE_HANDLER_CLASS',
    'pik.bus.consumer.MessageHandler'))


CHUNK_SIZE = 10000


@app.shared_task(bind=True)
def task_process_messages(self, pks, *args, **kwargs):
    qs = PIKMessageException.objects.filter(pk__in=pks).order_by('updated')

    task_id = self.request.id
    started = datetime.now()
    current = 0
    successful = 0
    failed = 0
    total = qs.count()

    register_progress(task_id, **{
        'total': total})

    try:
        for current, obj in enumerate(qs.iterator(chunk_size=CHUNK_SIZE), 1):
            handler = handler_class(obj.message, obj.queue, mdm_event_captor)
            if handler.handle():
                successful += 1
            else:
                failed += 1

            register_progress(task_id, **{
                'started': started,
                'current': current,
                'successful': successful,
                'failed': failed,
                'total': total,
                'finished': datetime.now()})

    except Exception as exc:  # noqa: broad-except
        capture_exception(exc)
        register_progress(task_id, **{
            'started': started,
            'current': current,
            'successful': successful,
            'failed': failed,
            'total': total,
            'finished': datetime.now(),
            'error': str(exc)})


@app.shared_task(bind=True)
def task_delete_messages(self, pks, *args, **kwargs):
    qs = PIKMessageException.objects.filter(pk__in=pks)

    task_id = self.request.id
    started = datetime.now()
    successful = 0
    failed = 0
    total = qs.count()

    register_progress(task_id, **{
        'total': total})

    for current, obj in enumerate(qs.iterator(chunk_size=CHUNK_SIZE), 1):
        try:
            obj.delete()
        except Exception as exc:  # noqa: broad-except
            capture_exception(exc)
            failed += 1
        else:
            successful += 1

        register_progress(task_id, **{
            'started': started,
            'current': current,
            'successful': successful,
            'failed': failed,
            'total': total,
            'error': None,
            'finished': datetime.now()})
