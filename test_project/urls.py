from django.contrib import admin
from django.urls import path, include

from pik.api.camelcase.router import CamelCaseRouter
from pik.api.deprecated.router import DeprecatedRouter

router_api_v1 = DeprecatedRouter()
router_api_v2 = CamelCaseRouter()

urlpatterns = [
    path('', include(('pik.oidc.urls', 'oidc'), namespace='auth-api')),
    path(r'admin/', admin.site.urls),
    path(r'api/v1/', include((router_api_v1.urls, 'api_v1'))),
    path(r'api/v2/', include((router_api_v2.urls, 'api_v2'))),
]
