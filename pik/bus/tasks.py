import logging
from datetime import datetime

from django.conf import settings
from django.utils.module_loading import import_string
from celery import app

from pik.utils.sentry import capture_exception
from pik.modeladmin.tasks import Action

from .mdm import mdm_event_captor
from .models import PIKMessageException


logger = logging.getLogger(__name__)
handler_class = import_string(getattr(
    settings, 'RABBITMQ_MESSAGE_HANDLER_CLASS',
    'pik.bus.consumer.MessageHandler'))


@app.shared_task(bind=True)
def task_process_messages(self, action_uid, pks, *args, **kwargs):
    qs = PIKMessageException.objects.filter(pk__in=pks).order_by('updated')

    action = Action(action_uid)
    action.set_values(started=datetime.now())
    try:
        for current, obj in enumerate(qs, 1):
            handler = handler_class(obj.message, obj.queue, mdm_event_captor)
            success = handler.handle()
            action.apply_message_status(success)
    except Exception as exc:  # noqa: broad-except
        capture_exception(exc)
        action.set_values(error=f'{exc.__class__.__name__}: {str(exc)}')


# @app.shared_task(bind=True)
# def task_delete_messages(self, pks, *args, **kwargs):
#     qs = PIKMessageException.objects.filter(pk__in=pks)
#
#     task_id = self.request.id
#     started = datetime.now()
#     successful = 0
#     failed = 0
#     total = qs.count()
#
#     set_progress(task_id, **{
#         'total': total})
#
#     for current, obj in enumerate(qs, 1):
#         try:
#             obj.delete()
#         except Exception as exc:  # noqa: broad-except
#             capture_exception(exc)
#             failed += 1
#         else:
#             successful += 1
#
#         set_progress(task_id, **{
#             'started': started,
#             'current': current,
#             'successful': successful,
#             'failed': failed,
#             'total': total,
#             'error': None,
#             'finished': datetime.now()})
