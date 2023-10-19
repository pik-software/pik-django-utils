import json

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from prettyjson.templatetags.prettyjson import prettyjson

from pik.modeladmin.modeladmin import AdminProgressMixIn

from .models import PIKMessageException
from .tasks import task_process_messages, task_delete_messages


@admin.register(PIKMessageException)
class PIKMessageExceptionAdmin(AdminProgressMixIn, admin.ModelAdmin):
    CHUNK_SIZE = 2**8

    page_contexts = ['get_progress_context']
    progress_pages = {'processing': _('Обработка'), 'deletion': _('Удаление')}

    list_display = ('queue', 'exception_type', 'entity_uid', )
    search_fields = (
        'created', 'queue', 'exception', 'exception_message', 'exception_type',
        'message', 'dependencies', 'entity_uid', )
    fields = (
        'created', 'queue', 'entity_uid', '_exception', 'exception_type',
        'exception_message', '_dependencies', '_message', )

    list_filter = ('exception_type', 'queue', 'has_dependencies')
    actions = ('_process_message', '_delete_selected')
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

    @admin.action(description=_('Обработать сообщения'))
    def _process_message(self, request, queryset):
        for chunk in self._split_sliced(queryset, self.CHUNK_SIZE):
            pks = [i.uid for i in chunk]
            task_process_messages.apply_async(kwargs={'pks': pks})

    @staticmethod
    def _split_sliced(sliced, chunk_size):
        for index in range(0, len(sliced), chunk_size):
            yield sliced[index:index + chunk_size]

    @admin.action(description=_('Удалить сообщения'))
    def _delete_selected(self, request, queryset):
        return self.execute_task_progress(
            'deletion', task_delete_messages, total=queryset.count(),
            kwargs={'pks': tuple(queryset.values_list('pk', flat=True))})

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
