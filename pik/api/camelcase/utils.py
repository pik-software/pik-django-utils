import re

from djangorestframework_camel_case.util import camelize_re
from djangorestframework_camel_case.util import underscore_to_camel


def camelize(data):
    if isinstance(data, str):
        data = re.sub(camelize_re, underscore_to_camel, data)

    return data
