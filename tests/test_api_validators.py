import uuid
from datetime import datetime

import pytest
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

import pik.api.serializers
from pik.api.exceptions import NewestUpdateValidationError
from pik.api.validators import NonChangeableValidator
from test_core_models.models.dated import MyDated
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


class MyDatedSerializer(pik.api.serializers.StandardizedModelSerializer):
    class Meta:
        model = MyDated
        fields = '__all__'


@pytest.mark.django_db
class TestNewestUpdateValidator:
    def test_update_fail(self):  # noqa: no-self-use
        past_datetime = datetime.strptime(
            '2001-01-01T00:00:00.000000', '%Y-%m-%dT%H:%M:%S.%f')

        my_dated = MyDated()
        my_dated.save()
        serializer = MyDatedSerializer(my_dated, {
            'created': my_dated.created,
            'updated': past_datetime})

        serializer.is_valid(raise_exception=True)
        serializer.save()
        assert serializer.instance == my_dated
        assert (
            serializer.instance.updated !=
            serializer.validated_data['updated'])
        assert past_datetime == serializer.validated_data['updated']
        assert (
            serializer.instance.updated !=
            past_datetime)

    def test_update_none_failed(self):  # noqa: no-self-use
        my_dated = MyDated()
        my_dated.save()
        serializer = MyDatedSerializer(my_dated, {
            'created': my_dated.created,
            'updated': None})

        with pytest.raises(ValidationError) as error:
            serializer.is_valid(raise_exception=True)
        assert not NewestUpdateValidationError.is_error_match(error.value)
