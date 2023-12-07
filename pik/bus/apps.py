from django.apps import AppConfig as BaseConfig
from django.utils.translation import gettext_lazy as _


class AppConfig(BaseConfig):
    name = 'pik.bus'
    verbose_name = _('Шина')

    def ready(self):
        from pik.bus.signals import produce_entity, produce_command_response  # noqa: import-outside-toplevel
        assert produce_entity  # noqa unused import
        assert produce_command_response  # noqa unused import
