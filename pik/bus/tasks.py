from datetime import datetime

from celery import app

from pik.utils.sentry import capture_exception
from pik.modeladmin.tasks import register_progress

from .consumer import MessageHandler
from .mdm import mdm_event_captor
from .models import PIKMessageException


@app.shared_task(bind=True)
def task_process_messages(self, pks, *args, **kwargs):

    current = 0
    failed = 0
    success = 0
    total = len(pks)
    started = datetime.now()
    task_id = self.request.id
    try:
        queryset = PIKMessageException.objects.filter(
            pk__in=pks).order_by('created')
        total = queryset.count()

        for current, obj in enumerate(queryset.iterator(), 1):
            handler = MessageHandler(obj.message, obj.queue, mdm_event_captor)
            if handler.handle():
                obj.delete()
                success += 1
            else:
                failed += 1

            register_progress(task_id, **{
                'started': started, 'current': current, 'total': total,
                'success': success, 'failed': failed})

            register_progress(task_id, **{
                'finished': datetime.now(),
                'started': started, 'current': current, 'total': total,
                'success': success, 'failed': failed})


    except Exception as exc:  # noqa: broad-except
        register_progress(task_id, **{
            'finished': datetime.now(),
            'current': current, 'total': total,
            'started': started, 'error': str(exc)})
        capture_exception(exc)


@app.shared_task(bind=True)
def task_delete_messages(self, pks, *args, **kwargs):
    started = datetime.now()
    task_id = self.request.id
    current = 0
    failed = 0
    success = 0
    total = len(pks)

    register_progress(task_id, **{
        'current': current, 'total': total,
        'started': started, 'error': None})

    qs = PIKMessageException.objects.filter(pk__in=pks)
    for current, obj in enumerate(qs, 1):
        try:
            obj.delete()
        except Exception as exc:  # noqa: broad-except
            capture_exception(exc)
            failed += 1
        else:
            success += 1

    register_progress(task_id, **{
        'finished': datetime.now(),
        'current': current, 'total': total,
        'started': started, 'error': None})
