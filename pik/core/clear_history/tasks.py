import math
from datetime import datetime, timedelta
from typing import List, Type, Union

from celery import app
from django.apps import apps
from django.conf import settings
from django.db import connection
from django.db.models import Model, Manager
from simple_history.models import HistoricalChanges
from tqdm import tqdm


@app.shared_task()
def clear_history():
    """Deletes oldest rows from history models."""
    keep_days = getattr(settings, 'HISTORY_CLEANING_KEEP_DAYS', 180)
    chunk_size = getattr(settings, 'HISTORY_CLEANING_CHUNK_SIZE', 10_000)
    deletion_date = datetime.now() - timedelta(days=keep_days)
    history_models: List[Type[Union[Model, HistoricalChanges]]] = [
        model for model in apps.get_models()
        if issubclass(model, HistoricalChanges)]

    for model_number, model in enumerate(history_models):
        deleting_objects: Manager = model.objects.filter(
            history_date__lte=deletion_date).order_by()
        objects_count = deleting_objects.count()
        model_label = (
            f'[{model_number + 1}/{len(history_models)}] {model._meta.label}')
        pbar = tqdm(total=objects_count, desc=model_label)
        for _ in range(math.ceil(objects_count / chunk_size)):
            deleted_count, _ = model.objects.filter(
                pk__in=deleting_objects.values_list(
                    'pk', flat=True
                )[:chunk_size]
            ).delete()
            pbar.update(deleted_count)
        if objects_count:
            with connection.cursor() as cursor:
                cursor.execute(f"VACUUM {model._meta.db_table};")
