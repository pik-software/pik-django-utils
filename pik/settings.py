from pik.oidc.settings import set_oidc_settings
from pik.bus.settings import LogstashLoggingSettingsExtendor


def _merge_oidc_settings(settings):
    set_oidc_settings(settings)


def _merge_bus_settings(settings):
    LogstashLoggingSettingsExtendor(settings).extend()


def merge_pik_settings(settings):
    _merge_oidc_settings(settings)
    _merge_bus_settings(settings)
