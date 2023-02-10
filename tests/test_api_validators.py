from datetime import datetime
import uuid
import pytest
from pprint import pformat
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, ErrorDetail

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
        'uid': str(uuid.uuid4())}
    instance = MyPUided(uid=payload['uid'])
    serializer = MyPUidedSerializer(instance, payload)
    serializer.is_valid(raise_exception=True)


class MyDatedSerializer(pik.api.serializers.StandardizedModelSerializer):
    class Meta:
        model = MyDated
        fields = '__all__'


@pytest.mark.django_db
class TestNewestUpdatedValidator:
    VALIDATION_ERROR = ValidationError({'updated': [ErrorDetail(
        string=('Новое значене поля updated должно быть больше предыдущего.'),
        code='newest_update_validation_error')]})

    def test_newest_update_validator_exception(self):
        past_datetime = datetime.strptime(
            '2001-01-01T00:00:00.000000', '%Y-%m-%dT%H:%M:%S.%f')

        my_dated = MyDated()
        my_dated.save()
        serializer = MyDatedSerializer(my_dated, {
            'created': my_dated.created,
            'updated': past_datetime})

        with pytest.raises(ValidationError) as error:
            serializer.is_valid(raise_exception=True)
        expected = ({'updated': [ErrorDetail(
            string='Новое значене поля updated должно быть больше '
                   'предыдущего.',
            code='newest_update_validation_error')]}, )
        assert error.value.args == expected
        assert NewestUpdateValidationError.is_error_match(error.value)

    def test_not_newest_update_validator_exception(self):
        my_dated = MyDated()
        my_dated.save()
        serializer = MyDatedSerializer(my_dated, {
            'created': my_dated.created,
            'updated': None})

        with pytest.raises(ValidationError) as error:
            serializer.is_valid(raise_exception=True)
        assert not NewestUpdateValidationError.is_error_match(error.value)

    def get_native_drf_validation_error(self):
        past_datetime = datetime.strptime(
            '2001-01-01T00:00:00.000000', '%Y-%m-%dT%H:%M:%S.%f')

        my_dated = MyDated()
        my_dated.save()
        serializer = MyDatedSerializer(my_dated, {
            'created': my_dated.created,
            'updated': past_datetime})

        with pytest.raises(ValidationError) as error:
            serializer.is_valid(raise_exception=True)
        return error.value

    def test_validation_error(self):
        drf_native_error = self.get_native_drf_validation_error()
        assert pformat(drf_native_error) == pformat(self.VALIDATION_ERROR)
