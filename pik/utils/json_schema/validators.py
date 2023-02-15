from functools import partial
from datetime import datetime

from jsonschema.validators import Draft202012Validator
from jsonschema import FormatChecker
from email_validator import validate_email, EmailNotValidError

from pik.utils.json_schema.exceptions import (
    DatetimeFormatValidationError, EmailFormatValidationError)


BaseSchemaValidator = Draft202012Validator


class BaseValidator:
    _value = None

    def __call__(self, value) -> bool:
        self._value = value
        if not isinstance(value, str):
            return True
        return all(map(lambda x: x(), self._all_checkers))

    @property
    def _all_checkers(self):
        return [
            getattr(self, method) for method in dir(self)
            if method.startswith('_check')]


class EmailValidator(BaseValidator):
    def _check_valid(self) -> bool:
        try:
            validate_email(self._value, check_deliverability=False)
            return True
        except EmailNotValidError as error:
            raise EmailFormatValidationError from error


class DatetimeValidator(BaseValidator):
    FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

    def _check_valid(self) -> bool:
        try:
            datetime.strptime(self._value, self.FORMAT)
            return True
        except ValueError as error:
            raise DatetimeFormatValidationError from error


format_checker = FormatChecker()
format_checker.checkers['email'] = (
    EmailValidator(), (EmailFormatValidationError, ))
format_checker.checkers['date-time'] = (
    DatetimeValidator(), (DatetimeFormatValidationError, ))
schema_validator = partial(
    BaseSchemaValidator, format_checker=format_checker)
