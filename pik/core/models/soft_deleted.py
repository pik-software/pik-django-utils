from django.db import models
from django.db.models import Q
from django.db.models.sql.where import WhereNode
from django.utils.translation import ugettext as _

from ._collector_delete import Collector

assert Collector.delete


class _BaseSoftDeletedQuerySet(models.QuerySet):
    def hard_delete(self):
        raise NotImplementedError()

    hard_delete.alters_data = True  # type: ignore
    hard_delete.queryset_only = True  # type: ignore

    def restore(self):
        return self.update(**{'deleted': None})

    restore.alters_data = True  # type: ignore
    restore.queryset_only = True  # type: ignore

    def get_restore_or_create(self, **kwargs):
        obj, created = self.model.all_objects.get_or_create(**kwargs)
        if not created and obj.deleted:
            obj.restore()
        return obj

    def update_restore_or_create(self, **kwargs):
        obj, created = self.model.all_objects.update_or_create(**kwargs)
        if not created and obj.deleted:
            obj.restore()
        return obj


class _AllWhereNode(WhereNode):
    pass


class _SoftDeletedObjectsWhereNode(WhereNode):
    pass


class _SoftObjectsWhereNode(WhereNode):
    pass


class SoftObjectsQuerySet(_BaseSoftDeletedQuerySet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query.where_class = _SoftObjectsWhereNode
        self.query.add_q(Q(deleted=None))


class SoftDeletedObjectsQuerySet(_BaseSoftDeletedQuerySet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query.where_class = _SoftDeletedObjectsWhereNode
        self.query.add_q(~Q(deleted=None))


class AllObjectsQuerySet(_BaseSoftDeletedQuerySet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query.where_class = _AllWhereNode


class SoftDeleted(models.Model):
    """
    Soft deletable model. Inspired by:
    https://lucasroesler.com/2017/04/delete-or-not-to-delete/
    """
    deleted = models.DateTimeField(
        editable=False, null=True, blank=True, verbose_name=_('Deleted')
    )

    objects = SoftObjectsQuerySet.as_manager()
    deleted_objects = SoftDeletedObjectsQuerySet.as_manager()
    all_objects = AllObjectsQuerySet.as_manager()

    def delete(self, using=None, keep_parents=False):
        if self.deleted:
            return 0, {}  # short-circuit here to prevent lots of nesting
        return super().delete(using=using, keep_parents=keep_parents)

    delete.alters_data = True  # type: ignore

    def hard_delete(self, *args, **kwargs):
        raise NotImplementedError()

    def restore(self):
        self.deleted = None
        self.save(update_fields=['deleted'])

    class Meta:
        abstract = True
