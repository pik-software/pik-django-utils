from django.http import HttpResponseForbidden
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from rest_framework import HTTP_HEADER_ENCODING
from social_core.exceptions import SocialAuthBaseException
from social_django.middleware import SocialAuthExceptionMiddleware


class OIDCExceptionMiddleware(SocialAuthExceptionMiddleware):
    def process_exception(self, request, exception):
        if not isinstance(exception, SocialAuthBaseException):
            return None
        return HttpResponseForbidden(self.get_message(request, exception))


class OIDCDefaultBackendMiddleware(MiddlewareMixin):
    @staticmethod
    def process_request(request):
        """ Backend forcing middleware """

        if not getattr(settings, 'OIDC_DEFAULT_BACKEND', None):
            return

        auth = request.META.get('HTTP_AUTHORIZATION', b'')
        if isinstance(auth, str):
            # Work around django test client oddness
            auth = auth.encode(HTTP_HEADER_ENCODING)

        auth = auth.decode(HTTP_HEADER_ENCODING).split()
        if len(auth) != 2:
            return

        prefix, token = auth
        request.META['HTTP_AUTHORIZATION'] = (
            f'{prefix} {settings.OIDC_DEFAULT_BACKEND} {token}')
