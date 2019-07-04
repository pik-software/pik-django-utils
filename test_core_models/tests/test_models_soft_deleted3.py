import pytest
from django.db.utils import IntegrityError
from django.utils.timezone import now

from pik.core.models._collector_delete import DeleteNotSoftDeletedModel  # noqa: protected access
from test_core_models import models


def test_soft_deleted_version_bumps():
    obj = models.MySoftDeleteModel.objects.create(name='test')

    assert obj.version == 1

    obj.delete()

    assert obj.version == 2


def test_soft_deleted_updated_changed():
    obj = models.MySoftDeleteModel.objects.create(name='test')

    old_updated = obj.updated

    obj.delete()

    assert obj.updated > old_updated


def test_historized_soft_deleted():
    obj = models.MySoftDeleteModel.objects.create(name='test')
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


def test_delete_soft_deleted_model_with_reverse_relation():
    obj = models.MySoftDeleteModel.objects.create(name='test')
    obj_with_rel = models.MyRelatedSoftDeletedModel.objects.create(
        name='super test', soft_deleted_fk=obj)

    old_obj_updated = obj.updated
    old_obj_with_rel_updated = obj_with_rel.updated

    obj.delete()
    obj_with_rel.refresh_from_db()

    assert obj.version == 2
    assert obj_with_rel.version == 2

    assert obj.deleted
    assert obj_with_rel.deleted

    assert obj.updated > old_obj_updated
    assert obj_with_rel.updated > old_obj_with_rel_updated


def test_restore_soft_deleted_model():
    obj = models.MySoftDeleteModel.objects.create(name='test')

    assert obj.version == 1

    obj.delete()

    updated_on_delete = obj.updated

    assert obj.deleted
    assert obj.version == 2

    obj.restore()

    assert not obj.deleted
    assert obj.version == 3
    assert obj.updated != updated_on_delete


def test_cascade_delete_with_fk_to_not_soft_deleted_model(settings):
    settings.SAFE_MODE = False
    not_soft_del_obj = models.MyNotSoftDeletedModel.objects.create(name='test')
    models.MySoftDeletedModelWithFK.objects.create(
        name='test soft', not_soft_deleted_fk=not_soft_del_obj)

    with pytest.raises(IntegrityError):
        not_soft_del_obj.delete()


def test_cascade_delete_with_fk_to_soft_deleted_model_failed(settings):
    settings.SAFE_MODE = True
    soft_del_obj = models.MySoftDeleteModel.objects.create(
        name='test soft')
    models.MyRelatedNotSoftDeletedModel.objects.create(
        name='test not soft', soft_deleted_fk=soft_del_obj)

    with pytest.raises(DeleteNotSoftDeletedModel):
        soft_del_obj.delete()


def test_cascade_delete_with_fk_to_soft_deleted_model_success(settings):
    settings.SAFE_MODE = False
    soft_del_obj = models.MySoftDeleteModel.objects.create(
        name='test soft')
    not_soft_del_obj = models.MyRelatedNotSoftDeletedModel.objects.create(
        name='test not soft', soft_deleted_fk=soft_del_obj)

    soft_del_obj.delete()

    with pytest.raises(models.MyRelatedNotSoftDeletedModel.DoesNotExist):
        not_soft_del_obj.refresh_from_db()


def test_cascade_soft_delete_with_already_deleted_model():
    soft_del_obj = models.MySoftDeleteModel.objects.create(
        name='test soft')
    soft_del_obj_with_rel = models.MyRelatedSoftDeletedModel.objects.create(
        name='test soft', soft_deleted_fk=soft_del_obj, deleted=now())

    old_updated = soft_del_obj_with_rel.updated

    soft_del_obj.delete()

    soft_del_obj_with_rel.refresh_from_db()

    assert old_updated == soft_del_obj_with_rel.updated


def test_not_soft_delete_without_safe_mode(settings):
    settings.SAFE_MODE = False
    obj = models.MyNotSoftDeletedModel.objects.create(
        name='test soft')

    obj.delete()


def test_hard_delete_with_safe_mode(settings):
    settings.SAFE_MODE = True
    obj = models.MySoftDeleteModel.objects.create(name="i'm gone")
    obj.hard_delete()

    with pytest.raises(models.MySoftDeleteModel.DoesNotExist):
        obj.refresh_from_db()


def test_hard_delete_without_safe_mode(settings):
    settings.SAFE_MODE = False
    obj = models.MySoftDeleteModel.objects.create(name="I'm gone too")
    obj.hard_delete()

    with pytest.raises(models.MySoftDeleteModel.DoesNotExist):
        obj.refresh_from_db()


def test_all_objects_is_deleted_filter(settings):
    settings.SAFE_MODE = True
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
