from django.contrib.contenttypes.models import ContentType
from django.db import models

from pik.core.models import SoftDeleted, BasePHistorical
from pik.core.models.fields import InheritPrimaryUidField


class _BaseBasePHistoricalTestModel(BasePHistorical):
    class Meta:
        abstract = True

    def __str__(self):
        return str(self.pk)


class MySoftDeleteModel(SoftDeleted, _BaseBasePHistoricalTestModel):
    name = models.CharField(max_length=255, blank=True, null=True)


class MyRelatedSoftDeletedModel(SoftDeleted, _BaseBasePHistoricalTestModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    soft_deleted_fk = models.ForeignKey(
        MySoftDeleteModel, on_delete=models.CASCADE)


class MyRelatedNullableSoftDeletedModel(SoftDeleted,
                                        _BaseBasePHistoricalTestModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    soft_deleted_fk = models.ForeignKey(
        MySoftDeleteModel, on_delete=models.SET_NULL, blank=True, null=True)


class MyRelatedNotSoftDeletedModel(_BaseBasePHistoricalTestModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    soft_deleted_fk = models.ForeignKey(
        MySoftDeleteModel, on_delete=models.CASCADE)


class MyNotSoftDeletedModel(_BaseBasePHistoricalTestModel):
    name = models.CharField(max_length=255, blank=True, null=True)


class MySoftDeletedModelWithFK(SoftDeleted, _BaseBasePHistoricalTestModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    not_soft_deleted_fk = models.ForeignKey(
        MyNotSoftDeletedModel, on_delete=models.CASCADE)


class TypeModel(models.Model):
    content_type = models.ForeignKey(
        ContentType, blank=True, null=True, on_delete=models.DO_NOTHING)

    class Meta:
        abstract = True


class ParentTypeSoftDeleteModel(
        TypeModel, SoftDeleted, _BaseBasePHistoricalTestModel):
    name = models.CharField(max_length=255, blank=True, null=True)


class ParentSoftDeleteModel(SoftDeleted, _BaseBasePHistoricalTestModel):
    ATTRED_TYPE_FIELD = 'type_model'

    name = models.CharField(max_length=255, blank=True, null=True)
    type_model = models.ForeignKey(
        ParentTypeSoftDeleteModel, on_delete=models.DO_NOTHING)


class ChildModel(models.Model):
    parent_model = None  # Use this field to store master table link
    ATTRED_TYPE_FIELD = None  # Must be defined in base class

    class Meta:
        abstract = True

    @classmethod
    def get_type_for_instance(cls):
        content_type = ContentType.objects.get_for_model(cls)
        field = getattr(cls._meta.model, cls.ATTRED_TYPE_FIELD).field  # noqa: pylint=protected-access
        type_model = field.related_model
        return type_model.objects.get(content_type=content_type)

    def save(self, *args, **kwargs):  # noqa: arguments-differ
        if self._state.adding:  # noqa: pylint=protected-access
            setattr(self, self.ATTRED_TYPE_FIELD, self.get_type_for_instance())
        super().save(*args, **kwargs)


class ChildMySoftDeleteModel(ParentSoftDeleteModel, ChildModel):
    parent_model = InheritPrimaryUidField(ParentSoftDeleteModel)
