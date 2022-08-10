import sys
from logging import getLogger

from sentry_sdk.utils import exc_info_from_error


logger = getLogger(__name__)


def capture_exception(error=None):
    """ Registering exception data through logs """

    if error is not None:
        exc_info = exc_info_from_error(error)
    else:
        exc_info = sys.exc_info()
    if not any(exc_info):
        raise ValueError('Unable to detect exception')
    logger.error("Exception is captured", exc_info=exc_info)
