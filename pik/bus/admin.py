import json

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from prettyjson.templatetags.prettyjson import prettyjson

from pik.modeladmin.modeladmin import AdminProgressMixIn

from .models import PIKMessageException
from .tasks import task_process_messages


@admin.register(PIKMessageException)
class PIKMessageExceptionAdmin(AdminProgressMixIn, admin.ModelAdmin):
    page_contexts = ['get_progress_context']
    progress_pages = {'processing': _('Обработка')}

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

    @admin.action(description='Обработать сообщения')
    def _process_message(self, request, queryset):
        return self.execute_task_progress(
            'processing', task_process_messages, total=queryset.count(),
            kwargs={'lookups': request.GET})
