from pik.bus.settings import LogstashBusLoggingSettingsExtender
from pik.oidc.settings import set_oidc_settings


def set_pik_settings(settings):
    set_oidc_settings(settings)
    LogstashBusLoggingSettingsExtender(settings).extend()
