from celery import app
from django.conf import settings
from simple_history.management.commands.clean_old_history import (
    Command as CleanOldHistoryCommand)


@app.shared_task()
def clear_history():
    """Deletes oldest rows from history models."""
    keep_days = getattr(settings, 'HISTORY_CLEANING_KEEP_DAYS', 180)
    cleaner = CleanOldHistoryCommand()
    cleaner.handle(auto=True, days=keep_days)
