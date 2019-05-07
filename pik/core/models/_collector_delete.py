# pylint: skip-file
from collections import Counter
from django.db.models.expressions import Col
from django.utils.timezone import now
from operator import attrgetter

from django.db import transaction
from django.db.models import signals, sql
from django.db.models.deletion import Collector
from django.db.models.fields.related import ForeignObject
from django.utils import six

FIELD = 'deleted'
IS_DELETED_FIELD = 'is_deleted'


def _delete(self):
    from .soft_deleted import SoftDeleted
    time = now()

    # sort instance collections
    for model, instances in self.data.items():
        self.data[model] = sorted(instances, key=attrgetter("pk"))

    # if possible, bring the models in an order suitable for databases that
    # don't support transactions or cannot defer constraint checks until the
    # end of a transaction.
    self.sort()
    # number of objects deleted for each model label
    deleted_counter = Counter()

    with transaction.atomic(using=self.using, savepoint=False):
        # send pre_delete signals
        for model, obj in self.instances_with_model():
            if not model._meta.auto_created:
                signals.pre_delete.send(
                    sender=model, instance=obj, using=self.using
                )

        # fast deletes
        for qs in self.fast_deletes:
            if issubclass(qs.model, SoftDeleted):
                pk_list = [obj.pk for obj in qs]
                qs = sql.UpdateQuery(qs.model)
                qs.update_batch(pk_list, {FIELD: time, IS_DELETED_FIELD: True},
                                self.using)
                count = len(pk_list)
            else:
                count = qs._raw_delete(using=self.using)
            deleted_counter[qs.model._meta.label] += count

        # update fields
        for model, instances_for_fieldvalues in six.iteritems(self.field_updates):
            for (field, value), instances in six.iteritems(instances_for_fieldvalues):
                query = sql.UpdateQuery(model)
                query.update_batch([obj.pk for obj in instances],
                                   {field.name: value}, self.using)

        # reverse instance collections
        for instances in six.itervalues(self.data):
            instances.reverse()

        # delete instances
        for model, instances in six.iteritems(self.data):
            if issubclass(model, SoftDeleted):
                query = sql.UpdateQuery(model)
                pk_list = [obj.pk for obj in instances]
                query.update_batch(
                    pk_list, {FIELD: time, IS_DELETED_FIELD: True}, self.using)
                for instance in instances:
                    setattr(instance, FIELD, time)
                    setattr(instance, IS_DELETED_FIELD, True)
                count = len(pk_list)
            else:
                query = sql.DeleteQuery(model)
                pk_list = [obj.pk for obj in instances]
                count = query.delete_batch(pk_list, self.using)
            deleted_counter[model._meta.label] += count

            if not model._meta.auto_created:
                for obj in instances:
                    signals.post_delete.send(
                        sender=model, instance=obj, using=self.using
                    )

    # update collected instances
    for model, instances_for_fieldvalues in six.iteritems(self.field_updates):
        for (field, value), instances in six.iteritems(instances_for_fieldvalues):
            for obj in instances:
                setattr(obj, field.attname, value)
    for model, instances in six.iteritems(self.data):
        for instance in instances:
            setattr(instance, model._meta.pk.attname, None)
    return sum(deleted_counter.values()), dict(deleted_counter)


def get_extra_restriction_patch(func):
    def wrapper(self, where_class, alias, related_alias):
        cond = func(self, where_class, alias, related_alias)

        from .soft_deleted import SoftDeleted, _AllWhereNode
        if not issubclass(self.model, SoftDeleted) or issubclass(where_class, _AllWhereNode):
            return cond

        cond = cond or where_class()
        field = self.model._meta.get_field(FIELD)
        lookup = field.get_lookup('isnull')(field.get_col(related_alias), True)
        cond.add(lookup, 'AND')

        return cond
    return wrapper


# MONKEY PATCHES

# we want to prevent hard delete for SoftDeleted models
Collector.delete = _delete
# we want to remove objects from related QS
ForeignObject.get_extra_restriction = get_extra_restriction_patch(ForeignObject.get_extra_restriction)
