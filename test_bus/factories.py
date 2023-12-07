from factory import SubFactory
from factory.django import DjangoModelFactory


from test_bus.models import TestRequestCommand, TestResponseCommand
from test_bus.constants import TEST_SERVICE, TEST_STATUS


class TestRequestCommandFactory(DjangoModelFactory):
    requesting_service = TEST_SERVICE

    class Meta:
        model = TestRequestCommand


class TestResponseCommandFactory(DjangoModelFactory):
    request = SubFactory(TestRequestCommandFactory)
    status = TEST_STATUS

    class Meta:
        model = TestResponseCommand
