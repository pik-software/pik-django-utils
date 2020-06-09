from collections import Counter
from operator import attrgetter

import six
from django.conf import settings
from django.db import transaction
from django.db.models import signals, sql
from django.db.models.deletion import Collector
from django.db.models.fields.related import ForeignObject
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

FIELD = 'deleted'


class DeleteNotSoftDeletedModel(Exception):
    pass


def _is_soft_excluded(model):
    soft_delete_exclude_list = getattr(settings, 'SOFT_DELETE_EXCLUDE', [])
    value = f'{model._meta.app_label}.{model._meta.object_name}'
    if value in soft_delete_exclude_list:
        return True
    return False


def _delete(self):
    from .soft_deleted import SoftDeleted
    safe_mode = getattr(settings, 'SOFT_DELETE_SAFE_MODE', True)

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
            if not model._meta.auto_created and not issubclass(  # noqa: pylint=protected-access
                    model, SoftDeleted):

                if safe_mode and not _is_soft_excluded(model):
                    raise DeleteNotSoftDeletedModel(
                        _(f'You are trying to delete {model._meta.object_name} instance,'
                          f' but {model._meta.object_name} is not subclass of '
                          f'{SoftDeleted._meta.object_name}. You need to inherit your '
                          f'model from {SoftDeleted._meta.object_name}'
                          f' or set settings.SOFT_DELETE_SAFE_MODE to False'))
                signals.pre_delete.send(
                    sender=model, instance=obj, using=self.using
                )

                # Do not send pre_delete signals because
                # we are using `.save()` for soft deletion.

        # fast deletes
        for qs in self.fast_deletes:
            if issubclass(qs.model, SoftDeleted):
                for obj in qs:
                    setattr(obj, FIELD, time)
                    obj.save()
                count = qs.count()
            else:
                count = qs._raw_delete(using=self.using)
            deleted_counter[qs.model._meta.label] += count

        # update fields
        for model, instances_for_fieldvalues in six.iteritems(self.field_updates):
            for (field, value), instances in six.iteritems(instances_for_fieldvalues):
                for obj in instances:
                    setattr(obj, field.name, value)
                    obj.save()

        # reverse instance collections
        for instances in six.itervalues(self.data):
            instances.reverse()

        # delete instances
        for model, instances in six.iteritems(self.data):
            if issubclass(model, SoftDeleted):
                count = len(instances)

                for instance in instances:
                    setattr(instance, FIELD, time)
                    instance.save()

                    # Do not send post_delete signal to prevent simple history
                    # from creating two records (change and deletion).
            else:

                query = sql.DeleteQuery(model)
                pk_list = [obj.pk for obj in instances]
                count = query.delete_batch(pk_list, self.using)

                if not model._meta.auto_created:
                    for obj in instances:
                        signals.post_delete.send(
                            sender=model, instance=obj, using=self.using
                        )

                # Set PK to None for non SoftDeleted models.
                # PK must be set to None AFTER sending `post_delete signal`
                # like in original `Collector.delete` method
                for obj in instances:
                    setattr(obj, model._meta.pk.attname, None)

            deleted_counter[model._meta.label] += count
    return sum(deleted_counter.values()), dict(deleted_counter)


def get_extra_restriction_patch(func):
    def wrapper(self, where_class, alias, related_alias):
        cond = func(self, where_class, alias, related_alias)

        from .soft_deleted import SoftDeleted, _AllWhereNode

        if not issubclass(self.model, SoftDeleted) or issubclass(where_class, _AllWhereNode):
            return cond
        for field in self.model._meta.fields:
            is_multitable_child = (
                    field.remote_field and field.primary_key and
                    issubclass(self.model, field.remote_field.model))

            if is_multitable_child:
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
