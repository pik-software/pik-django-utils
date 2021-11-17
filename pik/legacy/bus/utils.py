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
