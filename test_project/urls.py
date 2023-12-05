from django.contrib import admin
from django.urls import re_path, include

from pik.api.camelcase.router import CamelCaseRouter
from pik.api.deprecated.router import DeprecatedRouter

router_api_v1 = DeprecatedRouter()
router_api_v2 = CamelCaseRouter()

urlpatterns = [
    re_path('', include('pik.oidc.urls')),
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^api/v1/', include((router_api_v1.urls, 'api_v1'))),
    re_path(r'^api/v2/', include((router_api_v2.urls, 'api_v2'))),
]
