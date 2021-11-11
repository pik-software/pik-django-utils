import os
import platform
import django


def get_host():
    return {
        'machineName': platform.node(),
        'processId': os.getpid(),
        'frameworkVersion': django.get_version(),
        'operatingSystemVersion': f'{platform.system()} {platform.version()}'
    }


def get_message_type(model_class):
    return f'urn:message:{model_class.__module__}.{model_class.__name__}'


def get_queue_name(service_name, model_class):
    return f'{service_name}.{model_class.__name__}'
