from django.db import models

from pik.core.models import SoftDeleted


# Based on https://github.com/MnogoByte/django-permanent/blob/bdde297233eb7c83c862358854127c8654410aae/django_permanent/tests/test_app/models.py


class BaseTestModel(models.Model):
    class Meta:
        abstract = True

    def __str__(self):
        return str(self.pk)


class MyPermanentModel(SoftDeleted, BaseTestModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    pass


class RegularModel(BaseTestModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    pass


class RemovableRegularDepended(SoftDeleted, BaseTestModel):
    dependence = models.ForeignKey(RegularModel, on_delete=models.CASCADE)


class RemovableDepended(BaseTestModel):
    dependence = models.ForeignKey(MyPermanentModel, on_delete=models.CASCADE)


class NonRemovableDepended(SoftDeleted, BaseTestModel):
    dependence = models.ForeignKey(MyPermanentModel, on_delete=models.DO_NOTHING)


class NonRemovableNullableDepended(SoftDeleted, BaseTestModel):
    dependence = models.ForeignKey(MyPermanentModel, on_delete=models.SET_NULL, null=True)


class RemovableNullableDepended(SoftDeleted, BaseTestModel):
    dependence = models.ForeignKey(MyPermanentModel, on_delete=models.SET_NULL, null=True)


class PermanentDepended(SoftDeleted, BaseTestModel):
    dependence = models.ForeignKey(MyPermanentModel, on_delete=models.CASCADE)


class M2MFrom(BaseTestModel):
    pass


class PermanentM2MThrough(SoftDeleted):
    m2m_from = models.ForeignKey('M2MFrom', on_delete=models.CASCADE)
    m2m_to = models.ForeignKey('M2MTo', on_delete=models.CASCADE)


class M2MTo(SoftDeleted, BaseTestModel):
    m2m_from = models.ManyToManyField('M2MFrom', through=PermanentM2MThrough)
