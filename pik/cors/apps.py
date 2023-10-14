from django.apps import AppConfig as BaseAppConfig
from django.utils.translation import gettext_lazy as _


class AppConfig(BaseAppConfig):
    name = 'pik.cors'
    verbose_name = _('Кросс-доменные запросы (CORS)')
