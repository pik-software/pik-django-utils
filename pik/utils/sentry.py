import sys
from logging import getLogger

from sentry_sdk.utils import exc_info_from_error


logger = getLogger(__name__)


def capture_exception(error=None, message=''):
    """ Registering exception data through logs """

    if error is not None:
        exc_info = exc_info_from_error(error)
    else:
        exc_info = sys.exc_info()
    if not any(exc_info):
        raise ValueError('Unable to detect exception')
    logging_message = 'Exception is captured'
    if message:
        logging_message = f'{logging_message}: {message}'
    logger.error(logging_message, exc_info=exc_info)
