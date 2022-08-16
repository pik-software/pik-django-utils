import json

from django.contrib import admin, messages
from prettyjson.templatetags.prettyjson import prettyjson

from pik.bus.mdm import mdm_event_captor

from .consumer import MessageHandler
from .models import PIKMessageException


@admin.register(PIKMessageException)
class PIKMessageExceptionAdmin(admin.ModelAdmin):
    list_display = ('queue', 'exception_type', 'entity_uid', )
    search_fields = (
        'created', 'queue', 'exception', 'exception_message', 'exception_type',
        'message', 'dependencies', )
    fields = (
        'created', 'queue', 'entity_uid', '_exception', 'exception_type',
        'exception_message', '_dependencies', '_message', )

    list_filter = ('exception_type', 'queue', 'has_dependencies')
    actions = ('_process_message', )
    readonly_fields = fields

    @admin.display(description='Ошибка')
    def _exception(self, obj):  # noqa: no-self-use
        return prettyjson(
            obj.exception, initial='parsed', disabled='disabled')

    @admin.display(description='Зависимости')
    def _dependencies(self, obj):  # noqa: no-self-use
        return prettyjson(
            obj.dependencies, initial='parsed', disabled='disabled')

    @admin.display(description='Тело сообщения')
    def _message(self, obj):  # noqa: no-self-use
        try:
            return prettyjson(json.loads(
                bytes(obj.message)), initial='parsed', disabled='disabled')
        except json.JSONDecodeError:
            return bytes(obj.message)

    @admin.action(description='Обработать сообщение')
    def _process_message(self, request, queryset):
        success = 0
        failed = 0
        for obj in queryset.order_by('created'):
            handler = MessageHandler(obj.message, obj.queue, mdm_event_captor)
            if not handler.handle():
                failed += 1
                continue
            obj.delete()
            success += 1

        if failed and success:
            self.message_user(request, (
                f'Сообщений обработано успешно: {success}, c ошибкой: '
                f'{failed}.', messages.WARNING))
            return

        if success:
            self.message_user(request, (
                f'Успешно обработано сообщений: {success}', messages.SUCCESS))
            return

        if failed:
            self.message_user(request, (
                f'Сбой обработки, ошибок: {failed}', messages.ERROR))
