from django.db import models

from pik.core.models import SoftDeleted


class BaseModel(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)


class NullRelatedModel(models.Model):
    nullable_base = models.ForeignKey(BaseModel, blank=True, null=True,
                                      on_delete=models.CASCADE)


class BaseArchiveModel(SoftDeleted):
    name = models.CharField(max_length=100, blank=True, null=True)


class RelatedModel(models.Model):
    base = models.ForeignKey(BaseArchiveModel, on_delete=models.CASCADE)
    set_null_base = models.ForeignKey(
        BaseArchiveModel,
        blank=True, null=True, on_delete=models.deletion.SET_NULL)
    set_default_base = models.ForeignKey(
        BaseArchiveModel,
        blank=True, null=True, on_delete=models.deletion.SET_DEFAULT)


class RelatedCousinModel(models.Model):
    related = models.ForeignKey(RelatedModel, on_delete=models.CASCADE)
    set_null_related = models.ForeignKey(
        RelatedModel,
        blank=True, null=True, on_delete=models.deletion.SET_NULL)
    set_default_related = models.ForeignKey(
        RelatedModel,
        blank=True, null=True, on_delete=models.deletion.SET_DEFAULT)


class RelatedArchiveModel(SoftDeleted):
    base = models.ForeignKey(BaseArchiveModel, on_delete=models.CASCADE)
    set_null_base = models.ForeignKey(
        BaseArchiveModel,
        blank=True, null=True, on_delete=models.deletion.SET_NULL)
    set_default_base = models.ForeignKey(
        BaseArchiveModel,
        blank=True, null=True, on_delete=models.deletion.SET_DEFAULT)


class RelatedCousinArchiveModel(SoftDeleted):
    related = models.ForeignKey(RelatedArchiveModel, on_delete=models.CASCADE)
    set_null_related = models.ForeignKey(
        RelatedArchiveModel,
        blank=True, null=True, on_delete=models.deletion.SET_NULL)
    set_default_related = models.ForeignKey(
        RelatedArchiveModel,
        blank=True, null=True, on_delete=models.deletion.SET_DEFAULT)
