from django.conf.urls import include
from django.contrib import admin
from django.urls import re_path

from .views import (oidc_admin_login, oidc_admin_logout,
                    oidc_backchannel_logout, complete)


urlpatterns = [  # noqa: invalid-name

    # We need to override default `social_python` `complete` behavior in order
    # to provide backchannel logout implementation.
    re_path(r'^openid/complete/(?P<backend>[^/]+)/', complete),
    re_path(r'^openid/logout/(?P<backend>[^/]+)/$',
        oidc_backchannel_logout, name='oidc_backchannel_logout'),

    re_path(r'^openid/', include('social_django.urls', namespace='social')),
    re_path(r'^login/$', admin.site.login, name='login'),
    re_path(r'^logout/$', admin.site.logout, name='logout'),
    re_path(r'^admin/login/$', oidc_admin_login),
    re_path(r'^admin/logout/$', oidc_admin_logout),
]
