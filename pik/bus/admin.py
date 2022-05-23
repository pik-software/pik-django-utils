import json

from django.contrib import admin, messages
from prettyjson.templatetags.prettyjson import prettyjson

from .consumer import MessageHandler
from .models import PIKMessageException


@admin.register(PIKMessageException)
class PIKMessageExceptionAdmin(admin.ModelAdmin):
    list_display = ('queue', 'exception_type', 'entity_uid', )
    search_fields = (
        'queue', 'exception', 'exception_message', 'exception_type',
        'message', 'dependencies', )
    fields = (
        'queue', 'entity_uid', 'exception', 'exception_type',
        'exception_message', 'dependencies', '_message', )

    list_filter = ('exception_type', 'queue', )
    actions = ('_process_message', )
    readonly_fields = fields

    @admin.display(description='Тело сообщения')
    def _message(self, obj):  # noqa: no-self-use
        try:
            return prettyjson(json.loads(
                bytes(obj.message)), initial='parsed', disabled='disabled')
        except json.JSONDecodeError:
            return bytes(bytes(obj.message))

    @admin.action(description='Обработать сообщение')
    def _process_message(self, request, queryset):
        for obj in queryset:
            handler = MessageHandler(obj.message, obj.queue)
            if handler.handle():
                self.message_user(
                    request,
                    f'Сообщение {obj.uid} обработано', messages.SUCCESS)
                continue

            self.message_user(
                request, (
                    f'Ошибка обратки сообщения {obj.uid}: '
                    f'{handler.exc_data["message"]}'),
                level=messages.ERROR)
