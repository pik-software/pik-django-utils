from test_core_shortcuts.tests.factories import MyDjangoModelFactory
from ..models import (
    MyDated, MyOwned, MyNullOwned, MyUided, MyPUided,
    MyVersioned, MyStrictVersioned, MyHistorized, MyBasePHistorical,
    MyBaseHistorical)


class MyDatedFactory(MyDjangoModelFactory):
    class Meta:
        model = MyDated


class MyOwnedFactory(MyDjangoModelFactory):
    class Meta:
        model = MyOwned


class MyNullOwnedFactory(MyDjangoModelFactory):
    class Meta:
        model = MyNullOwned


class MyUidedFactory(MyDjangoModelFactory):
    class Meta:
        model = MyUided


class MyPUidedFactory(MyDjangoModelFactory):
    class Meta:
        model = MyPUided


class MyVersionedFactory(MyDjangoModelFactory):
    class Meta:
        model = MyVersioned


class MyStrictVersionedFactory(MyDjangoModelFactory):
    class Meta:
        model = MyStrictVersioned


class MyHistorizedFactory(MyDjangoModelFactory):
    class Meta:
        model = MyHistorized


class MyBasePHistoricalFactory(MyDjangoModelFactory):
    class Meta:
        model = MyBasePHistorical


class MyBaseHistoricalFactory(MyDjangoModelFactory):
    class Meta:
        model = MyBaseHistorical
