from django.apps import AppConfig as BaseConfig
from django.utils.translation import gettext_lazy as _


class AppConfig(BaseConfig):
    name = 'pik.bus'
    verbose_name = _('Шина')

    def ready(self):
        from pik.bus.producer import push_model_instance_to_rabbit_queue  ## noqa: import-outside-toplevel
        assert push_model_instance_to_rabbit_queue  # noqa unused import
