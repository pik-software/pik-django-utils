from django.db.models.signals import post_delete, post_save
from django.test import TestCase
from django.utils.timezone import now

from ..models import RegularModel, RemovableRegularDepended
from ..models import (
    M2MFrom,
    M2MTo,
    MyPermanentModel,
    NonRemovableDepended,
    NonRemovableNullableDepended,
    RemovableNullableDepended,
    PermanentDepended,
    PermanentM2MThrough,
    RemovableDepended,
)

# This file based on
# https://github.com/MnogoByte/django-permanent/blob/bdde297233eb7c83c862358854127c8654410aae/django_permanent/tests/cases.py


class TestDelete(TestCase):
    def setUp(self):
        self.permanent = MyPermanentModel.objects.create()

    def test_deletion(self):
        model = MyPermanentModel
        permanent2 = model.objects.create()
        self.permanent.delete()
        self.assertTrue(self.permanent.deleted)
        self.assertEqual(list(model.objects.all()), [permanent2])
        self.assertEqual(list(model.all_objects.all()), [self.permanent, permanent2])
        self.assertEqual(list(model.deleted_objects.all()), [self.permanent])

    def test_depended(self):
        model = RemovableDepended
        model.objects.create(dependence=self.permanent)
        with self.settings(SOFT_DELETE_SAFE_MODE=False):
            self.permanent.delete()
        self.assertEqual(list(model.objects.all()), [])

    def test_non_removable_depended(self):
        model = NonRemovableDepended
        depended = model.objects.create(dependence=self.permanent)
        self.permanent.delete()
        self.assertEqual(list(model.objects.all()), [depended])

    def test_non_removable_nullable_depended(self):
        model = NonRemovableNullableDepended
        model.objects.create(dependence=self.permanent)
        self.permanent.delete()
        depended = model.objects.first()
        self.assertEqual(depended.dependence, None)

    def test_removable_nullable_depended(self):
        model = RemovableNullableDepended
        model.objects.create(dependence=self.permanent)
        self.permanent.delete()
        depended = model.objects.first()
        self.assertEqual(depended.dependence, None)

    def test_remove_removable_nullable_depended(self):
        model = RemovableRegularDepended
        test_model = model.objects.create(dependence=RegularModel.objects.create(name='Test'))
        test_model.delete()
        self.assertIsNotNone(model.deleted_objects.first().dependence)

    def test_permanent_depended(self):
        model = PermanentDepended
        depended = model.objects.create(dependence=self.permanent)
        self.permanent.delete()
        self.assertEqual(list(model.objects.all()), [])
        self.assertEqual(list(model.deleted_objects.all()), [depended])
        new_depended = model.all_objects.get(pk=depended.pk)
        new_permanent = MyPermanentModel.all_objects.get(pk=self.permanent.pk)
        self.assertTrue(new_depended.deleted)
        self.assertTrue(new_permanent.deleted)
        self.assertEqual(new_depended.dependence_id, self.permanent.id)

    def test_related(self):
        p = PermanentDepended.objects.create(dependence=self.permanent)
        self.permanent.delete()
        self.assertEqual(list(PermanentDepended.all_objects.select_related('dependence').all()), [p])

    def test_double_delete(self):
        self.called_post_delete = 0
        self.called_post_save = 0

        def post_delete_receiver(*args, **kwargs):
            self.called_post_delete += 1

        def post_save_receiver(*args, **kwargs):
            self.called_post_save += 1

        post_delete.connect(post_delete_receiver, sender=PermanentDepended)
        post_save.connect(post_save_receiver, sender=PermanentDepended)

        model = PermanentDepended
        model.objects.create(dependence=self.permanent, deleted=now())
        self.permanent.delete()
        # because we don't called pre/post delete signals on
        # softdeleted modelds
        self.assertEqual(self.called_post_delete, 0)
        self.assertEqual(self.called_post_save, 1)

    def test_restore(self):
        self.called_pre = 0
        self.called_post = 0

        def pre_restore_receiver(sender, instance, **kwargs):
            self.called_pre += 1

        def post_restore_receiver(sender, instance, **kwargs):
            self.called_post += 1

        # pre_restore.connect(pre_restore_receiver)
        # post_restore.connect(post_restore_receiver)

        self.permanent.delete()
        self.permanent.restore()
        self.assertFalse(self.permanent.deleted)
        self.assertEqual(list(MyPermanentModel.objects.all()), [self.permanent])

        # pre_restore.disconnect(pre_restore_receiver)
        # post_restore.disconnect(post_restore_receiver)

        # self.assertEqual(self.called_pre, 1)
        # self.assertEqual(self.called_post, 1)


class TestIntegration(TestCase):
    def test_prefetch_bug(self):
        permanent1 = MyPermanentModel.objects.create()
        NonRemovableDepended.objects.create(dependence=permanent1)
        MyPermanentModel.objects.prefetch_related('nonremovabledepended_set').all()
        NonRemovableDepended.all_objects.prefetch_related('dependence').all()

    def test_related_manager_bug(self):
        permanent = MyPermanentModel.objects.create()
        PermanentDepended.objects.create(dependence=permanent)
        PermanentDepended.objects.create(dependence=permanent, deleted=now())
        self.assertEqual(permanent.permanentdepended_set.count(), 1)
        self.assertEqual(PermanentDepended.objects.count(), 1)

    def test_m2m_manager(self):
        _from = M2MFrom.objects.create()
        _to = M2MTo.objects.create()
        PermanentM2MThrough.objects.create(m2m_from=_from, m2m_to=_to, deleted=now())
        self.assertEqual(_from.m2mto_set.count(), 0)

    def test_m2m_manager_clear(self):
        _from = M2MFrom.objects.create()
        _to = M2MTo.objects.create()
        PermanentM2MThrough.objects.create(m2m_from=_from, m2m_to=_to)
        self.assertEqual(_from.m2mto_set.count(), 1)
        _from.m2mto_set.clear()
        self.assertEqual(_from.m2mto_set.count(), 0)
        self.assertEqual(PermanentM2MThrough.objects.count(), 0)
        self.assertEqual(PermanentM2MThrough.all_objects.count(), 1)
        self.assertEqual(M2MFrom.objects.count(), 1)
        self.assertEqual(M2MTo.objects.count(), 1)

    def test_m2m_manager_delete(self):
        _from = M2MFrom.objects.create()
        _to = M2MTo.objects.create()
        PermanentM2MThrough.objects.create(m2m_from=_from, m2m_to=_to)
        self.assertEqual(_from.m2mto_set.count(), 1)
        _from.m2mto_set.all().delete()
        self.assertEqual(_from.m2mto_set.count(), 0)
        self.assertEqual(M2MFrom.objects.count(), 1)
        self.assertEqual(M2MTo.objects.count(), 0)
        self.assertEqual(PermanentM2MThrough.objects.count(), 0)
        self.assertEqual(PermanentM2MThrough.all_objects.count(), 1)

    def test_m2m_manager_delete_obj(self):
        _from = M2MFrom.objects.create()
        _to = M2MTo.objects.create()
        PermanentM2MThrough.objects.create(m2m_from=_from, m2m_to=_to)
        self.assertEqual(_from.m2mto_set.count(), 1)
        print(_to.delete())
        self.assertEqual(_from.m2mto_set.count(), 0)
        self.assertEqual(M2MFrom.objects.count(), 1)
        self.assertEqual(M2MTo.objects.count(), 0)
        self.assertEqual(PermanentM2MThrough.objects.count(), 0)
        self.assertEqual(PermanentM2MThrough.all_objects.count(), 1)

    def test_m2m_prefetch_related(self):
        _from = M2MFrom.objects.create()
        _to = M2MTo.objects.create()
        PermanentM2MThrough.objects.create(m2m_from=_from, m2m_to=_to)
        PermanentM2MThrough.objects.create(m2m_from=_from, m2m_to=_to, deleted=now())
        self.assertSequenceEqual(M2MFrom.objects.prefetch_related('m2mto_set').get(pk=_from.pk).m2mto_set.all(), [_to])
        self.assertEqual(M2MFrom.objects.prefetch_related('m2mto_set').get(pk=_from.pk).m2mto_set.count(), 1)

    def test_m2m_all_objects(self):
        dependence = MyPermanentModel.objects.create(deleted=now())
        depended = NonRemovableDepended.objects.create(dependence=dependence, deleted=now())
        depended = NonRemovableDepended.all_objects.get(pk=depended.pk)
        self.assertEqual(depended.dependence, dependence)

    def test_m2m_deleted_through(self):
        _from = M2MFrom.objects.create()
        _to = M2MTo.objects.create()
        PermanentM2MThrough.objects.create(m2m_from=_from, m2m_to=_to, deleted=now())
        self.assertEqual(M2MFrom.objects.filter(m2mto__id=_to.pk).count(), 0)


class TestCustomQSMethods(TestCase):
    def test_get_restore_or_create__get(self):
        self.obj = MyPermanentModel.objects.create(name="old")
        self.assertEqual(MyPermanentModel.objects.get_restore_or_create(name="old").id, 1)

    def test_get_restore_or_create__restore(self):
        self.called_pre = 0
        self.called_post = 0

        def pre_restore_receiver(sender, instance, **kwargs):
            self.called_pre += 1

        def post_restore_receiver(sender, instance, **kwargs):
            self.called_post += 1

        # pre_restore.connect(pre_restore_receiver)
        # post_restore.connect(post_restore_receiver)

        obj = MyPermanentModel.objects.create(name="old", deleted=now())
        self.assertEqual(MyPermanentModel.objects.get_restore_or_create(name="old").id, obj.id)
        self.assertEqual(MyPermanentModel.objects.count(), 1)
        self.assertEqual(MyPermanentModel.all_objects.count(), 1)

        # pre_restore.disconnect(pre_restore_receiver)
        # post_restore.disconnect(post_restore_receiver)

        # self.assertEqual(self.called_pre, 1)
        # self.assertEqual(self.called_post, 1)

    def test_get_restore_or_create__create(self):
        MyPermanentModel.objects.get_restore_or_create(name="old")
        self.assertEqual(MyPermanentModel.objects.get_restore_or_create(name="old").id, 1)
        self.assertEqual(MyPermanentModel.objects.count(), 1)
        self.assertEqual(MyPermanentModel.all_objects.count(), 1)

    def test_restore(self):
        MyPermanentModel.objects.create(name="old", deleted=now())
        MyPermanentModel.deleted_objects.filter(name="old").restore()
        self.assertEqual(MyPermanentModel.objects.count(), 1)
        self.assertEqual(MyPermanentModel.all_objects.count(), 1)

    def test_update_restore_or_create__update(self):
        self.obj = MyPermanentModel.objects.create(name="old")
        self.assertEqual(MyPermanentModel.objects.update_restore_or_create(id=self.obj.id, defaults={'name': 'new'}).name, 'new')

    def test_update_restore_or_create__restore(self):
        self.called_pre = 0
        self.called_post = 0

        def pre_restore_receiver(sender, instance, **kwargs):
            self.called_pre += 1

        def post_restore_receiver(sender, instance, **kwargs):
            self.called_post += 1

        # pre_restore.connect(pre_restore_receiver)
        # post_restore.connect(post_restore_receiver)

        obj = MyPermanentModel.objects.create(name="old", deleted=now())
        self.assertEqual(MyPermanentModel.objects.update_restore_or_create(id=obj.id, defaults={'name': 'new'}).name, 'new')
        self.assertEqual(MyPermanentModel.objects.count(), 1)
        self.assertEqual(MyPermanentModel.all_objects.count(), 1)

        # pre_restore.disconnect(pre_restore_receiver)
        # post_restore.disconnect(post_restore_receiver)

        # self.assertEqual(self.called_pre, 1)
        # self.assertEqual(self.called_post, 1)

    def test_update_restore_or_create__create(self):
        MyPermanentModel.objects.update_restore_or_create(name="old")
        self.assertEqual(MyPermanentModel.objects.update_restore_or_create(name="old").id, 1)
        self.assertEqual(MyPermanentModel.objects.count(), 1)
        self.assertEqual(MyPermanentModel.all_objects.count(), 1)
