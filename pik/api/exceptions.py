from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import (
    APIException, ValidationError, ErrorDetail)


class APIRequestError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST


class NewestUpdateValidationError(ValidationError):
    """
    The serializer.is_valid method always returns a ValidationError exception,
    regardless of the type of exception returned by the validator.
    To determine the type of validator, we use the code field of ErrorDetail.
    """

    error_msg = _('Новое значене поля updated должно быть больше предыдущего.')
    code = 'newest_update_validation_error'

    def __init__(self):
        super().__init__(ErrorDetail(self.error_msg, code=self.code))

    @staticmethod
    def is_error_match(error: Exception):
        if not isinstance(error, ValidationError):
            return False
        updated = error.args[0].get('updated')
        if not updated:
            return False
        return updated[0].code == NewestUpdateValidationError.code


def extract_exception_data(exc):
    code = getattr(exc, 'default_code', exc.__class__.__name__)
    detail = getattr(exc, 'detail', str(exc))
    if getattr(detail, 'code', None):
        code = exc.detail.code

    if isinstance(detail, (list, dict)):
        return {
            'code': code,
            'detail': exc.get_full_details(),
            'message': str(exc.default_detail),
        }
    return {
        'code': code,
        'message': str(detail),
    }
