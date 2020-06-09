from django.contrib.admin.utils import NestedObjects
from django.core.exceptions import FieldDoesNotExist
from django.db import models, router, transaction
from django.db.models import Q
from django.db.models.sql import DeleteQuery
from django.db.models.sql.where import WhereNode
from django.utils.translation import gettext_lazy as _
from ._collector_delete import Collector

assert Collector.delete


def _get_field_by_name(model, field):
    """
    Retrieve a field instance from a model by its name.
    """
    field_dict = {x.name: x for x in model._meta.get_fields()}  # noqa
    return field_dict[field]


def _has_field(model, field):
    try:
        model._meta.get_field(field)  # noqa
        return True
    except FieldDoesNotExist:
        return False


def _cascade_soft_delete(inst_or_qs, using, keep_parents=False):
    """
    Return collector instance that has marked ArchiveMixin instances for
    archive (i.e. update) instead of actual delete.
    Arguments:
        inst_or_qs (models.Model or models.QuerySet): the instance(s) that
            are to be deleted.
        using (db connection/router): the db to delete from.
        keep_parents (bool): defaults to False.  Determine if cascade is true.
    Returns:
        models.deletion.Collector: this is a standard Collector instance but
            the ArchiveMixin instances are in the fields for update list.
    """
    if not isinstance(inst_or_qs, models.QuerySet):
        instances = [inst_or_qs]
    else:
        instances = inst_or_qs

    # The collector will iteratively crawl the relationships and
    # create a list of models and instances that are connected to
    # this instance.
    collector = NestedObjects(using=using)
    collector.collect(instances, keep_parents=keep_parents)
    if collector.protected:
        raise models.ProtectedError("Delete protected", collector.protected)
    collector.sort()

    return collector


def _delete_collected(collector):
    with transaction.atomic(using=collector.using, savepoint=False):
        return collector.delete()


class _BaseSoftDeletedQuerySet(models.QuerySet):
    def delete(self):
        # doing an update is the most efficient, but does not promise
        # that the cascade will happen. E.g.
        # return self.update(deleted_on=timezone.now())

        # from django source
        # https://github.com/django/django/blob/1.8.6/django/db/models/query.py
        # Line: #L516
        assert self.query.can_filter(), \
            "Cannot use 'limit' or 'offset' with delete."

        # iterating and deleting ensures that the cascade delete will
        # occur for each instance.
        collector = _cascade_soft_delete(self.all(), self.db)
        self._result_cache = None
        return _delete_collected(collector)

    delete.alters_data = True  # type: ignore
    delete.queryset_only = True  # type: ignore

    def hard_delete(self):
        return models.QuerySet.delete(self)

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

    def is_deleted(self):
        return self.filter(deleted__isnull=False)

    def is_not_deleted(self):
        return self.filter(deleted__isnull=True)


class SoftDeleted(models.Model):
    """
    Soft deletable model. Inspired by:
    https://lucasroesler.com/2017/04/delete-or-not-to-delete/

    If you want to use SoftDeleted with unique constraint there are
    a problem because NULL != NULL.
    You can use workaround with `UniqueConstraint in django>=2.2
    https://docs.djangoproject.com/en/2.2/ref/models/constraints/#django.db.models.UniqueConstraint
    """
    deleted = models.DateTimeField(
        editable=False, null=True, blank=True, verbose_name=_('Deleted')
    )

    objects = SoftObjectsQuerySet.as_manager()
    deleted_objects = SoftDeletedObjectsQuerySet.as_manager()
    all_objects = AllObjectsQuerySet.as_manager()

    def delete(self, using=None, keep_parents=False):
        using = using or router.db_for_write(self.__class__, instance=self)

        assert self._get_pk_val() is not None, \
            "%s object can't be deleted because its %s attribute " \
            "is set to None." % (self._meta.object_name, self._meta.pk.attname)

        if self.deleted:
            return 0, {}  # short-circuit here to prevent lots of nesting

        collector = _cascade_soft_delete(self, using, keep_parents)
        return _delete_collected(collector)

    delete.alters_data = True  # type: ignore

    def hard_delete(self):
        using = router.db_for_write(self.__class__, instance=self)
        delete_query = DeleteQuery(self._meta.model)
        result = delete_query.delete_batch([self.pk], using)
        self.pk = None  # noqa: pylint=invalid-name
        return result

    def restore(self):
        self.deleted = None
        self.save()

    class Meta:
        abstract = True
