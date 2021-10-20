import warnings
from .renderers import *  # noqa


warnings.warn(
    "`renderer` module is deprecated use `renderers` instead",
    DeprecationWarning,
    stacklevel=2)  # noqa
