import uuid
import pytest
from django.db import models
from django.db.models import UUIDField
from rest_framework import serializers
from pik.api.validators import NonChangeableValidator


class ModelForTest(models.Model):
    uid = UUIDField()

    class Meta:
        app_label = ''


class SerializerForTest(serializers.ModelSerializer):
    uid = serializers.UUIDField(
        validators=[
            NonChangeableValidator(),
        ],
    )

    class Meta:
        model = ModelForTest
        fields = ['uid']


@pytest.mark.django_db
def test_non_changeable_validator():
    payload = {
        'uid': str(uuid.uuid4())
    }
    instance = ModelForTest(uid=payload['uid'])
    serializer = SerializerForTest(instance, payload)
    serializer.is_valid(raise_exception=True)
