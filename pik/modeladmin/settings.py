from django.conf import settings

from pik.admin import use_latin_permissions


def set_permission_settings():
    if getattr(settings, 'USE_DJANGO_ADMIN_LATIN_PERMISSION_NAMES', None):
        use_latin_permissions()
