from django.urls.conf import include, re_path, path
from django.contrib import admin

from .views import (
    oidc_admin_login, oidc_admin_logout, oidc_backchannel_logout, complete)


urlpatterns = [  # noqa: invalid-name
    # We need to override default `social_python` `complete` behavior in order
    # to provide backchannel logout implementation.
    re_path(
        r'^openid/complete/(?P<backend>[^/]+)/', complete),
    re_path(
        r'^openid/logout/(?P<backend>[^/]+)/$',
        oidc_backchannel_logout, name='oidc_backchannel_logout'),

    path(r'openid/', include('social_django.urls', namespace='social')),
    path(r'login/', admin.site.login, name='login'),
    path(r'logout/', admin.site.logout, name='logout'),
    path(r'admin/login/', oidc_admin_login),
    path(r'admin/logout/', oidc_admin_logout),
]
