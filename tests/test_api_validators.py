from datetime import datetime
import uuid
import pytest
from rest_framework import serializers

import pik.api.serializers
from pik.api.validators import NonChangeableValidator
from pik.api.exceptions import NewestUpdateValidationError
from test_core_models.models.uided import MyPUided
from test_core_models.models.dated import MyDated


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


class MyDatedSerializer(pik.api.serializers.StandardizedModelSerializer):
    class Meta:
        model = MyDated
        fields = '__all__'


@pytest.mark.django_db
class TestNewestUpdateValidator:
    def test_newest_update_validator_exception(self):
        past_datetime = datetime.strptime(
            '2001-01-01T00:00:00.000000', '%Y-%m-%dT%H:%M:%S.%f')

        my_dated = MyDated()
        my_dated.save()
        serializer = MyDatedSerializer(my_dated, {
            'created': my_dated.created,
            'updated': past_datetime})

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as error:
            assert NewestUpdateValidationError.is_error_match(error)

    def test_not_newest_update_validator_exception(self):
        my_dated = MyDated()
        my_dated.save()
        serializer = MyDatedSerializer(my_dated, {
            'created': my_dated.created,
            'updated': None})

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as error:
            assert not NewestUpdateValidationError.is_error_match(error)

