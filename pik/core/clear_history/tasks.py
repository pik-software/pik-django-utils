import logging
import math

from celery import app
from django.conf import settings
from django.utils import timezone
from simple_history import models, utils
from simple_history.exceptions import NotHistoricalModelError

LOGGER = logging.getLogger(__name__)


def _get_models():
    to_process = set()
    for model in models.registered_models.values():
        try:  # avoid issues with multi-table inheritance
            history_model = utils.get_history_model_for_model(model)
        except NotHistoricalModelError:
            continue
        to_process.add((model, history_model))
    return to_process


@app.shared_task()
def clear_history():
    """Deletes oldest rows from history models."""
    keep_days = getattr(settings, 'HISTORY_CLEANING_KEEP_DAYS', 180)
    chunk_size = getattr(settings, 'HISTORY_CLEANING_CHUNK_SIZE', 10_000)

    to_process = _get_models()
    start_date = timezone.now() - timezone.timedelta(days=keep_days)

    for model, history_model in to_process:
        history_model_manager = history_model.objects
        history_model_manager = history_model_manager.filter(
            history_date__lt=start_date
        ).order_by()
        found = history_model_manager.count()
        LOGGER.info("%s has %s old historical entries", model, found)
        if not found:
            continue
        for _ in range(math.ceil(found / chunk_size)):
            history_model_manager[:chunk_size].delete()
        LOGGER.info("Removed %s historical records for %s", found, model)
