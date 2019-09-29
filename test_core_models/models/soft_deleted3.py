from django.db import models

from pik.core.models import SoftDeleted, BasePHistorical


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
