from pik.api.serializers import StandardizedModelSerializer

from test_bus.models import TestRequestCommand


class TestRequestCommandSerializer(StandardizedModelSerializer):
    class Meta:
        model = TestRequestCommand
        fields = ('guid', 'type', 'requesting_service')


class TestResponseCommandSerializer(StandardizedModelSerializer):
    class Meta:
        model = TestRequestCommand
        fields = ('guid', 'type', 'request', 'status', 'error')
