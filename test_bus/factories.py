from factory import SubFactory, Faker
from factory.django import DjangoModelFactory


from test_bus.models import MyTestEntity, MyTestRequestCommand, MyTestResponseCommand
from test_bus.constants import TEST_SERVICE, TEST_STATUS


class MyTestEntityFactory(DjangoModelFactory):
    uid = Faker('uuid4')

    class Meta:
        model = MyTestEntity


class MyTestRequestCommandFactory(DjangoModelFactory):
    requesting_service = TEST_SERVICE

    class Meta:
        model = MyTestRequestCommand


class MyTestResponseCommandFactory(DjangoModelFactory):
    request = SubFactory(MyTestRequestCommandFactory)
    status = TEST_STATUS

    class Meta:
        model = MyTestResponseCommand


    # created = Faker('date_time_this_decade')
    # name = 'ass'
