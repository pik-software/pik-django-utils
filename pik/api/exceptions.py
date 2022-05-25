from rest_framework import status
from rest_framework.exceptions import APIException


class APIRequestError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST


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
