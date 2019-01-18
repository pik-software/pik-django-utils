from django.db import models
from pik.core.models import BasePHistorical
from pik.core.models.fields import InheritPrimaryUidField


class Building(BasePHistorical):
    address = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f'{self.uid}'


class Apartment(Building):
    building_ptr = InheritPrimaryUidField(Building)


class Parking(Building):
    building_ptr = InheritPrimaryUidField(Building)


class BuildingPart(BasePHistorical):
    building = models.ForeignKey(Building, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.building_id} -> {self.uid}'


class Stairwell(BuildingPart):
    buildingpart_ptr = InheritPrimaryUidField(BuildingPart)


class Garret(BuildingPart):
    buildingpart_ptr = InheritPrimaryUidField(BuildingPart)
