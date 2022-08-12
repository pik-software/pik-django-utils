import json

from django.contrib import admin, messages
from prettyjson.templatetags.prettyjson import prettyjson

from pik.bus.mdm import mdm_event_captor

from .consumer import MessageHandler
from .models import PIKMessageException


class IsDependencyExceptionFilter(admin.SimpleListFilter):
    title = 'Ошибка зависимости'
    parameter_name = 'is_dependency_error'

    def lookups(self, request, model_admin):
        return (
            ('true', 'Да'),
            ('false', 'Нет'),
        )

    def queryset(self, request, queryset):
        if self.value() and self.value().lower() in ('true', '1'):
            return queryset.exclude(dependencies={})
        if self.value() and self.value().lower() in ('false', '0'):
            return queryset.filter(dependencies={})
        return queryset


@admin.register(PIKMessageException)
class PIKMessageExceptionAdmin(admin.ModelAdmin):
    list_display = ('queue', 'exception_type', 'entity_uid', )
    search_fields = (
        'created', 'queue', 'exception', 'exception_message', 'exception_type',
        'message', 'dependencies', )
    fields = (
        'created', 'queue', 'entity_uid', '_exception', 'exception_type',
        'exception_message', '_dependencies', '_message', )

    list_filter = ('exception_type', 'queue', IsDependencyExceptionFilter)
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
        for obj in queryset.order_by('created'):
            handler = MessageHandler(obj.message, obj.queue, mdm_event_captor)
            if handler.handle():
                self.message_user(
                    request,
                    f'Сообщение {obj.uid} обработано', messages.SUCCESS)
                obj.delete()
                continue

            self.message_user(
                request, (
                    f'Ошибка обработки сообщения {obj.uid}: '
                    f'{handler.exc_data["message"]}'),
                level=messages.ERROR)
