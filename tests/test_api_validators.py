import uuid
import pytest
from rest_framework import serializers
from pik.api.validators import NonChangeableValidator
from test_core_models.models.uided import MyPUided


class MyPUidedSerializer(serializers.ModelSerializer):
    uid = serializers.UUIDField(
        validators=[
            NonChangeableValidator(),
        ],
    )

    class Meta:
        model = MyPUided
        fields = ['uid']


@pytest.mark.django_db
def test_non_changeable_validator():
    payload = {
        'uid': str(uuid.uuid4())
    }
    instance = MyPUided(uid=payload['uid'])
    serializer = MyPUidedSerializer(instance, payload)
    serializer.is_valid(raise_exception=True)
