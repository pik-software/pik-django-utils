import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now

from pik.core.models._collector_delete import DeleteNotSoftDeletedModel  # noqa: protected access
from test_core_models import models


class TestDeleteSoftDeletedModel:

    model = models.MySoftDeleteModel

    def test_delete(self):
        obj = self.model.objects.create(name='test')
        old_updated = obj.updated

        obj.delete()

        assert obj.pk is not None
        assert obj.version == 2
        assert obj.deleted is not None
        assert obj.updated > old_updated

    def test_delete_historized(self):
        obj = self.model.objects.create(name='test')
        history = obj.history.all()
        assert obj.history
        assert obj.history.count() == 1

        obj.save()
        assert obj.history.count() == 2

        obj.delete()
        assert obj.history.count() == 3
        assert history.count() == 3

        hist_obj1 = history.last()
        hist_obj2 = history[1]
        hist_obj3 = history.first()
        assert isinstance(hist_obj3.history_id, int)
        assert hist_obj3.pk == hist_obj3.history_id
        assert hist_obj3.history_change_reason is None
        assert hist_obj3.history_id > hist_obj1.history_id

        assert hist_obj1.history_type == '+'
        assert hist_obj2.history_type == '~'
        assert hist_obj3.history_type == '~'

    def test_restore(self):
        obj = self.model.objects.create(name='test', deleted=now())
        old_updated = obj.updated

        obj.restore()

        assert obj.deleted is None
        assert obj.version == 2
        assert old_updated < obj.updated

    @pytest.mark.parametrize('safe_mode', [True, False])
    def test_hard_delete_instance(self, settings, safe_mode):
        settings.SOFT_DELETE_SAFE_MODE = safe_mode
        obj = self.model.objects.create(name="i'm gone")
        uid = obj.uid

        obj.hard_delete()

        assert self.model.all_objects.filter(uid=uid).exists() is False
        assert obj.pk is None


class TestDeletedRelatedModel:

    not_soft_deleted_model = models.MyNotSoftDeletedModel

    model = models.MySoftDeleteModel
    related_model = models.MyRelatedSoftDeletedModel
    nullable_related_model = models.MyRelatedNullableSoftDeletedModel

    def test_cascade_delete(self):
        obj = self.model.objects.create(name='test')
        related_obj = self.related_model.objects.create(
            name='test_related', soft_deleted_fk=obj)
        obj_pk = obj.pk
        related_obj_pk = related_obj.pk

        obj.delete()
        related_obj.refresh_from_db()

        assert obj.pk is not None
        assert obj.deleted is not None
        assert related_obj.pk is not None
        assert related_obj.deleted is not None
        assert obj.version == 2
        assert related_obj.version == 2
        assert self.model.all_objects.filter(pk=obj_pk).exists() is True
        assert self.related_model.all_objects.filter(
            pk=related_obj_pk).exists() is True

    def test_set_null_delete(self):
        obj = self.model.objects.create(name='test')
        related_obj = self.nullable_related_model.objects.create(
            name='test_related', soft_deleted_fk=obj)
        obj_pk = obj.pk
        related_obj_pk = related_obj.pk

        obj.delete()
        related_obj.refresh_from_db()

        assert obj.pk is not None
        assert obj.deleted is not None
        assert related_obj.pk is not None
        assert related_obj.deleted is None
        assert related_obj.soft_deleted_fk is None
        assert obj.version == 2
        assert related_obj.version == 2
        assert self.model.all_objects.filter(pk=obj_pk).exists() is True
        assert self.nullable_related_model.objects.filter(
            pk=related_obj_pk).exists() is True

    def test_cascade_with_already_deleted(self):
        soft_del_obj = self.model.objects.create(name='test soft')
        soft_del_obj_with_rel = self.related_model.objects.create(
            name='test soft', soft_deleted_fk=soft_del_obj, deleted=now())
        old_updated = soft_del_obj_with_rel.updated

        soft_del_obj.delete()
        soft_del_obj_with_rel.refresh_from_db()

        assert old_updated == soft_del_obj_with_rel.updated

    def test_delete_cascade_not_soft_deleted_forbidden(self, settings):
        settings.SOFT_DELETE_SAFE_MODE = True
        soft_del_obj = self.model.objects.create(
            name='test soft')
        models.MyRelatedNotSoftDeletedModel.objects.create(
            name='test not soft', soft_deleted_fk=soft_del_obj)

        with pytest.raises(DeleteNotSoftDeletedModel):
            soft_del_obj.delete()

    def test_delete_cascade_not_soft_deleted(self, settings):
        settings.SOFT_DELETE_SAFE_MODE = False
        soft_del_obj = self.model.objects.create(
            name='test soft')
        not_soft_del_obj = models.MyRelatedNotSoftDeletedModel.objects.create(
            name='test not soft', soft_deleted_fk=soft_del_obj)
        not_soft_del_uid = not_soft_del_obj.pk

        soft_del_obj.delete()

        assert soft_del_obj.pk is not None
        assert soft_del_obj.deleted is not None
        assert soft_del_obj.version == 2
        assert self.model.all_objects.filter(
            pk=soft_del_obj.pk).exists() is True
        assert models.MyRelatedNotSoftDeletedModel.objects.filter(
            pk=not_soft_del_uid).exists() is False


def test_all_objects_is_deleted_filter(settings):
    settings.SOFT_DELETE_SAFE_MODE = True
    obj1 = models.MySoftDeleteModel.objects.create(name="obj 1")
    obj2 = models.MySoftDeleteModel.objects.create(name="obj 2")
    obj3 = models.MySoftDeleteModel.objects.create(name="obj 3")

    obj2.delete()
    obj3.delete()

    assert 3 == len(models.MySoftDeleteModel.all_objects.all())

    is_deleted_qs = models.MySoftDeleteModel.all_objects.is_deleted()
    assert 2 == len(is_deleted_qs)
    assert obj2 in is_deleted_qs
    assert obj3 in is_deleted_qs

    is_not_deleted_qs = models.MySoftDeleteModel.all_objects.is_not_deleted()
    assert 1 == len(is_not_deleted_qs)
    assert obj1 in is_not_deleted_qs


def test_deleted_model_from_exclude_list(settings):
    settings.SOFT_DELETE_SAFE_MODE = True
    settings.SOFT_DELETE_EXCLUDE = ['auth.User']

    User = get_user_model()
    user = User.objects.create(username='test_user')
    pk = user.pk
    user.delete()

    assert user.pk is None
    assert User.objects.filter(pk=pk).exists() is False


def test_delete_not_soft_deleted(settings):
    settings.SOFT_DELETE_SAFE_MODE = False
    obj = models.MyNotSoftDeletedModel.objects.create(name='test')
    obj_pk = obj.pk

    obj.delete()

    assert obj.pk is None
    assert models.MyNotSoftDeletedModel.objects.filter(
        pk=obj_pk).exists() is False


def test_delete_parent_soft_deleted():
    type_obj = models.ParentTypeSoftDeleteModel.objects.create(
        name='type_name')
    obj = models.ParentSoftDeleteModel.objects.create(
        name='test', type_model=type_obj)
    obj.delete()

    assert 1 == models.ParentSoftDeleteModel.all_objects.count()
    assert 0 == models.ParentSoftDeleteModel.objects.count()


def test_delete_child_soft_deleted():
    content_type = ContentType.objects.get_for_model(
        models.ChildMySoftDeleteModel)
    type_obj = models.ParentTypeSoftDeleteModel.objects.create(
        name='type_name')
    type_obj.content_type = content_type
    type_obj.save()
    obj = models.ChildMySoftDeleteModel.objects.create(name='child name')
    obj.delete()

    assert 1 == models.ParentSoftDeleteModel.all_objects.count()
    assert 0 == models.ParentSoftDeleteModel.objects.count()
    assert 1 == models.ChildMySoftDeleteModel.all_objects.count()
    assert 0 == models.ChildMySoftDeleteModel.objects.count()
