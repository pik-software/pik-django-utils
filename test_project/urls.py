from django.contrib import admin
from django.urls import re_path, include

urlpatterns = [
    re_path('', include('pik.oidc.urls')),
    re_path(r'^admin/', admin.site.urls),
]
