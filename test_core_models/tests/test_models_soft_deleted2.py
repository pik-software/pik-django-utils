from test_core_models import models


def test_built_in_cascade(settings):
    """
    Verifies cascade deletion
    """
    settings.SAFE_MODE = False

    base = models.BaseModel.objects.create(name='test')
    models.NullRelatedModel.objects.create(nullable_base=base)

    base.delete()
    assert not (models.NullRelatedModel.objects.exists())


def test_cascade_delete(settings):
    """
    Verify that if we delete a model with the ArchiveMixin, then the
    delete cascades to its "parents", i.e. the models with foreign keys
    to it.
    """
    settings.SAFE_MODE = False
    base = models.BaseArchiveModel.objects.create(name='test')
    related = models.RelatedModel.objects.create(base=base)
    models.RelatedCousinModel.objects.create(related=related)
    related_archivable = models.RelatedArchiveModel.objects.create(
        base=base)
    cousin_archivable = models.RelatedCousinArchiveModel.objects.create(
        related=related_archivable)

    base.delete()

    assert not (models.RelatedModel.objects.exists())
    assert not (models.RelatedCousinModel.objects.exists())

    assert not (models.RelatedArchiveModel.objects.exists())
    assert (models.RelatedArchiveModel.all_objects.exists())
    related_archivable = models.RelatedArchiveModel.all_objects.get(
        pk=related_archivable.pk)
    assert (related_archivable.deleted) is not None

    assert not (models.RelatedCousinArchiveModel.objects.exists())
    assert (models.RelatedCousinArchiveModel.all_objects.exists())
    cousin_archivable = models.RelatedCousinArchiveModel.all_objects.get(
        pk=cousin_archivable.pk)
    assert (cousin_archivable.deleted) is not None


def test_cascade_delete_qs(settings):
    """
    Verify that if we delete a model with the ArchiveMixin, then the
    delete cascades to its "parents", i.e. the models with foreign keys
    to it.
    """
    settings.SAFE_MODE = False
    base = models.BaseArchiveModel.objects.create(name='test')
    models.BaseArchiveModel.objects.create(name='test')
    models.BaseArchiveModel.objects.create(name='test')
    related = models.RelatedModel.objects.create(base=base)
    models.RelatedCousinModel.objects.create(related=related)
    related_archivable = models.RelatedArchiveModel.objects.create(
        base=base)
    models.RelatedCousinArchiveModel.objects.create(
        related=related_archivable)

    models.BaseArchiveModel.objects.all().delete()

    assert not (models.RelatedModel.objects.exists())
    assert not (models.RelatedCousinModel.objects.exists())
    assert not (models.RelatedArchiveModel.objects.exists())
    assert (models.RelatedArchiveModel.all_objects.exists())
    assert not (models.RelatedCousinArchiveModel.objects.exists())
    assert (models.RelatedCousinArchiveModel.all_objects.exists())


def test_cascade_nullable():
    """
    Verify that related models are deleted even if the relation is
    nullable.
    """
    base = models.BaseArchiveModel.objects.create(name='test')
    base2 = models.BaseArchiveModel.objects.create(name='test2')
    related = models.RelatedModel.objects.create(
        base=base, set_null_base=base2, set_default_base=base2)
    archivable_related = models.RelatedArchiveModel.objects.create(
        base=base, set_null_base=base2, set_default_base=base2)
    models.RelatedCousinModel.objects.create(related=related)
    models.RelatedCousinArchiveModel.objects.create(
        related=archivable_related)

    base2.delete()

    assert 1 == models.BaseArchiveModel.objects.count()
    assert 1 == models.RelatedModel.objects.count()
    assert 1 == models.RelatedArchiveModel.objects.count()
    assert 1 == models.RelatedCousinModel.objects.count()
    assert 1 == models.RelatedCousinArchiveModel.objects.count()


def test_cascade_set_null():
    """
    Verify that related models are not deleted if on_delete is SET_NULL
    """
    base = models.BaseArchiveModel.objects.create(name='test')
    base2 = models.BaseArchiveModel.objects.create(name='test2')
    related = models.RelatedModel.objects.create(
        base=base, set_null_base=base2)
    models.RelatedCousinModel.objects.create(related=related)

    base2.delete()

    assert 1 == models.BaseArchiveModel.objects.count()
    assert 1 == models.RelatedModel.objects.count()
    assert 1 == models.RelatedCousinModel.objects.count()

    assert (
        models.RelatedModel.objects.filter(pk=related.pk).exists())


def test_cascade_set_null_qs():
    """
    Verify that related models are not deleted if on_delete is SET_NULL
    """
    base = models.BaseArchiveModel.objects.create(name='test')
    base2 = models.BaseArchiveModel.objects.create(name='test2')
    related = models.RelatedModel.objects.create(
        base=base, set_null_base=base2)
    models.RelatedCousinModel.objects.create(related=related)

    models.BaseArchiveModel.objects.filter(pk=base2.pk).delete()

    assert 1 == models.BaseArchiveModel.objects.count()
    assert 1 == models.RelatedModel.objects.count()
    assert 1 == models.RelatedCousinModel.objects.count()

    assert (
        models.RelatedModel.objects.filter(pk=related.pk).exists())


def test_cascade_set_default():
    """
    Verify that related models are not deleted if on_delete is SET_DEFAULT
    """
    base = models.BaseArchiveModel.objects.create(name='test')
    base2 = models.BaseArchiveModel.objects.create(name='test2')
    related = models.RelatedModel.objects.create(
        base=base, set_default_base=base2)
    models.RelatedCousinModel.objects.create(related=related)

    base2.delete()

    assert 1 == models.BaseArchiveModel.objects.count()
    assert 1 == models.RelatedModel.objects.count()
    assert 1 == models.RelatedCousinModel.objects.count()

    assert models.RelatedModel.objects.filter(pk=related.pk).exists()
