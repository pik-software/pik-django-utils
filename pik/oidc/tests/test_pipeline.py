import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group


from pik.oidc.pipeline import actualize_roles


@pytest.fixture
def user():
    return get_user_model().objects.create(username="testuser")


@pytest.mark.django_db
def test_actualize_roles_system(user):  # noqa: pylint - redefined-outer-name
    group = Group.objects.create(name='sys-group')
    group.user_set.add(user)

    actualize_roles(user=user, response={'access_token': 'access_token'})

    assert (set(user.groups.values_list('name', flat=True)) ==
            {'sys-group', 'default'})


@pytest.mark.django_db
def test_actualize_roles_extra(user):  # noqa: pylint - redefined-outer-name
    actualize_roles(user=user, response={'access_token': 'access_token',
                                         'roles': [{'name': 'extra'}]})

    assert (set(user.groups.values_list('name', flat=True)) ==
            {'default', 'extra'})


@pytest.mark.django_db
def test_actualize_roles_redundant(user):  # noqa: pylint - redefined-outer-name
    group = Group.objects.create(name='redundant')
    group.user_set.add(user)

    actualize_roles(user=user, response={'access_token': 'access_token'})

    assert set(user.groups.values_list('name', flat=True)) == {'default'}
