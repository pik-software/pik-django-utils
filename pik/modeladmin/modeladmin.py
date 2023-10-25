import re
from datetime import datetime, timedelta
from functools import partial, update_wrapper
from math import ceil
from typing import Optional, Dict

from django.contrib.admin import ModelAdmin
from django.contrib.gis import admin
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from simple_history.admin import SimpleHistoryAdmin

from pik.core.permitted_fields.admin import (
    PermittedFieldsAdminMixIn, PermittedFieldsInlineAdminMixIn)
from pik.utils.itertools import batched

from .tasks import PIKProgressor


class ReasonedMixIn:
    def save_model(self, request, obj, form, change):
        # add `changeReason` for simple-history
        change_prefix = f'Admin: changed by {request.user}: '
        if not change:
            obj.changeReason = f'Admin: created by {request.user}: {repr(obj)}'
        elif form.changed_data:
            obj.changeReason = change_prefix + f'{repr(form.changed_data)}'
        else:
            obj.changeReason = change_prefix + 'save() without changes'
        if len(obj.changeReason) > 100:
            obj.changeReason = obj.changeReason[0:97] + '...'
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        # add `changeReason` for simple-history
        obj.changeReason = f'Admin: deleted by {request.user}: {repr(obj)}'
        if len(obj.changeReason) > 100:
            obj.changeReason = obj.changeReason[0:97] + '...'
        super().delete_model(request, obj)


class NonDeletableModelAdminMixIn:
    def has_delete_permission(self, request, obj=None):  # noqa: pylint=no-self-use
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class NonAddableModelAdminMixIn:
    def has_add_permission(self, request):  # noqa: pylint=no-self-use
        return False


class StrictMixIn(NonAddableModelAdminMixIn, NonDeletableModelAdminMixIn):
    pass


class SecuredModelAdmin(PermittedFieldsAdminMixIn, ReasonedMixIn,
                        admin.ModelAdmin):
    pass


class StrictSecuredModelAdmin(StrictMixIn, SecuredModelAdmin):
    pass


class SecuredAdminInline(PermittedFieldsInlineAdminMixIn, ReasonedMixIn,
                         admin.TabularInline):
    extra = 0


class StrictSecuredAdminInline(StrictMixIn, SecuredAdminInline):
    pass


class VersionedModelAdmin(SimpleHistoryAdmin):
    pass


class SecuredVersionedModelAdmin(VersionedModelAdmin, SecuredModelAdmin):
    pass


class StrictSecuredVersionedModelAdmin(StrictMixIn, VersionedModelAdmin,
                                       SecuredModelAdmin):
    pass


class RequiredInlineMixIn:
    validate_min = True
    extra = 0
    min_num = 1

    def get_formset(self, *args, **kwargs):  # noqa: pylint=arguments-differ
        return super().get_formset(validate_min=self.validate_min, *args,
                                   **kwargs)


class AutoSetRequestUserMixIn:
    def save_model(self, request, obj, form, change):
        if hasattr(obj, 'user_id') and not obj.user_id:
            obj.user_id = request.user.pk
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        for formset in formsets:
            instances = formset.save(commit=False)
            for instance in instances:
                if hasattr(instance, 'user_id') and not instance.user_id:
                    instance.user_id = request.user.pk
        super().save_related(request, form, formsets, change)


def admin_page(function=None, **kwargs):
    def decorator(func):
        for key, value in kwargs.items():
            setattr(func, key, value)
        return func
    if function is None:
        return decorator
    return decorator(function)


class AdminPageMixIn(ModelAdmin):
    """
        MixIn allowing custom admin pages creation

        1. Define and register context getter
        ```python
            class MyModelAdmin:
                page_contexts = ['get_page_context']
                def get_page_context(request)
                    return {...}
        ```
        2 Customize context getter
        ```python
                def get_page_context(request)
                    return {...}
                get_page_context.slug = ''
                get_page_context.url_pattern = ''
                get_page_context.title = ''
                get_page_context.template = ''
                get_page_context.permission = ''
        ```python
        3 Override response
        ```
            def get_page_context(request):
                return HttpRedirect('/')
        ```

    """
    page_contexts: Optional[list] = None

    def get_page_contexts(self):
        return self.page_contexts

    def get_urls(self):
        if not self.get_page_contexts():
            return super().get_urls()

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            wrapper.model_admin = self
            return update_wrapper(wrapper, view)

        urls = [*super().get_urls()]
        for context_getter_name in self.get_page_contexts():
            props = self.get_context_getter_props(context_getter_name)
            urls.append((path(
                props['url_pattern'], wrap(partial(
                    self.page_view, context_getter_name=context_getter_name)),
                name=props["full_slug"])))
        return urls

    def page_view(self, request, context_getter_name, *args, **kwargs):
        props = self.get_context_getter_props(context_getter_name)
        response = getattr(self, context_getter_name)(
            request=request, *args, **kwargs)
        if isinstance(response, HttpResponse):
            return response
        return TemplateResponse(request, props['template'], {
            'model': self.model, 'opts': self.model._meta, **props,
            'has_view_permission': self.has_view_permission(request),
            **response})

    def get_context_getter_props(self, context_getter_name):
        context_getter = getattr(self, context_getter_name)
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        slug = re.sub('^get_|_context$', '',  context_getter_name)
        full_slug = f'{app_label}_{model_name}_page_{slug}'
        context_getter_data = {
            'slug': slug,
            'full_slug': full_slug,
            'url_name': full_slug,
            'url_pattern': f'page/{slug}',
            'title': slug.replace('_', '').capitalize(),
            'template': 'admin/page.html',
            'permission': full_slug}

        return {
            key: getattr(context_getter, key, value)
            for key, value in context_getter_data.items()}


class AdminProgressMixIn(AdminPageMixIn):
    CHUNK_SIZE = 2**13

    page_contexts = ['get_progress_context']
    progress_pages: Optional[Dict[str, str]] = None

    def execute_task_progress(self, name, task, queryset, progress_id):
        self._run_tasks(task, queryset, progress_id)
        return HttpResponseRedirect(self.get_progress_url(name, progress_id))

    def _run_tasks(self, task, queryset, progress_id):
        progressor = PIKProgressor(progress_id)
        progressor.set_values(started=datetime.now(), total=queryset.count())
        for chunk in batched(queryset, self.CHUNK_SIZE):
            kwargs = {
                'progress_id': progress_id,
                'pks': [obj.uid for obj in chunk]}
            task.apply_async(kwargs=kwargs)

    @admin_page(
        template='admin/progress.html',
        url_pattern='page/progress/<path:process>/<path:progress_id>')
    def get_progress_context(self, request, process, progress_id):
        return self.render_progress(request, process, progress_id)

    def render_progress(self, request, name, progress_id, **kwargs):
        progressor = PIKProgressor(progress_id)
        progress = progressor.get_progress()
        if progress is None:
            raise Http404('Task not found')
        return {
            **self.admin_site.each_context(request),
            **self._get_progress_context(progress),
            'title': self.progress_pages[name],
            **kwargs}

    @staticmethod
    def _get_progress_context(progress):
        started = progress['started']
        finished = progress['finished']
        processed = progress['successful'] + progress['failed']
        total = progress['total']
        last_time = finished or datetime.now()
        seconds = (last_time - started).total_seconds() if started else None
        elapsed = timedelta(seconds=ceil(seconds)) if seconds else None
        speed = (
            processed / elapsed.total_seconds()
            if processed and elapsed else None)
        failed = progress['failed']
        percent = ceil(100 * processed / total)
        eta = (
            timedelta(seconds=ceil((total - processed) / speed))
            if speed else None)
        error = progress['error']

        return {
            'started': started,
            'processed': processed,
            'total': total,
            'elapsed': elapsed,
            'speed': speed,
            'failed': failed,
            'percent': percent,
            'eta': eta,
            'error': error,
            'finished': finished}

    def get_progress_url(self, process, task_id):
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        return reverse(f'admin:{app_label}_{model_name}_page_progress', args=(
            process, task_id))
