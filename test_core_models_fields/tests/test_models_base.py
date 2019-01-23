import pytest
from django.utils.crypto import get_random_string
from django.db.utils import IntegrityError

from ..models import Building, Apartment, Parking


def test_create_parent_without_child():
    addr1 = get_random_string()
    Building.objects.create(address=addr1)
    assert Building.objects.filter(address=addr1).count() == 1
    assert Apartment.objects.filter(address=addr1).count() == 0
    assert Parking.objects.filter(address=addr1).count() == 0


def test_every_child_will_create_new_parent():
    Parking.objects.create(address=get_random_string())
    Apartment.objects.create(address=get_random_string())
    Building.objects.create(address=get_random_string())
    assert Building.objects.all().count() == 3
    assert Apartment.objects.all().count() == 1
    assert Parking.objects.all().count() == 1


def test_child_will_create_new_parent_with_the_same_address_and_uid():
    addr1 = get_random_string()
    Parking.objects.create(address=addr1)
    assert Building.objects.all().count() == 1
    assert Apartment.objects.all().count() == 0
    assert Parking.objects.all().count() == 1

    building = Building.objects.all()[0]
    assert building.address == addr1
    parking = Parking.objects.all()[0]
    assert parking.address == addr1
    assert building.uid == parking.uid


def test_parent_address_unique_constraint():
    addr1 = get_random_string()
    Building.objects.create(address=addr1)
    with pytest.raises(IntegrityError):
        Parking.objects.create(address=addr1)
    assert Building.objects.filter(address=addr1).count() == 1
    assert Apartment.objects.filter(address=addr1).count() == 0
    assert Parking.objects.filter(address=addr1).count() == 0


def test_child_ptr_uid_the_same_as_parent():
    parking = Parking.objects.create(address=get_random_string())
    assert parking.uid == parking.building_ptr.uid
