import django

if django.VERSION < (3, 2, 0):
    default_app_config = 'pik.cors.apps.AppConfig'  # noqa: invalid-name
