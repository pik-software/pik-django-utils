import uuid
import pytest
from django.db import models
from django.db.models import UUIDField
from rest_framework import serializers
from pik.api.validators import NonChangeableValidator


class TestModel(models.Model):
    uid = UUIDField()

    class Meta:
        app_label = ''


class TestSerializer(serializers.ModelSerializer):
    uid = serializers.UUIDField(
        validators=[
            NonChangeableValidator(),
        ],
    )

    class Meta:
        model = TestModel
        fields = ['uid']


@pytest.mark.django_db
def test_non_changeable_validator():
    payload = {
        'uid': str(uuid.uuid4())
    }
    instance = TestModel(uid=payload['uid'])
    serializer = TestSerializer(instance, payload)
    serializer.is_valid(raise_exception=True)
