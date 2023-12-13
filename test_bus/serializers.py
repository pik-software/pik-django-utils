from pik.api.serializers import StandardizedModelSerializer

from test_bus.models import (
    MyTestEntity, MyTestRequestCommand, MyTestResponseCommand)


class MyTestEntitySerializer(StandardizedModelSerializer):
    class Meta:
        model = MyTestEntity
        fields = ('guid', 'type')


class MyTestRequestCommandSerializer(StandardizedModelSerializer):
    class Meta:
        model = MyTestRequestCommand
        fields = ('guid', 'type', 'requesting_service')


class MyTestResponseCommandSerializer(StandardizedModelSerializer):
    class Meta:
        model = MyTestResponseCommand
        fields = ('guid', 'type', 'request', 'status', 'error')
