from contextlib import nullcontext
import pytest
from jsonschema.exceptions import ValidationError

from pik.utils.json_schema.validators import (
    DatetimeValidator, EmailValidator, schema_validator)
from pik.utils.json_schema.exceptions import (
    DatetimeFormatValidationError, EmailFormatValidationError)


class TestEmailFormatValidator:
    SUCCESS = nullcontext()
    FAIL = pytest.raises(EmailFormatValidationError)

    @pytest.mark.parametrize(
        'value, raise_context', [
            (None, SUCCESS),
            ('username@hostname.ru', SUCCESS),
            ('имяпользователя@домен.рф', SUCCESS),
            ('userимя@доменhost.рф', SUCCESS),
            # According rfc6761 'invalid' domain - guaranteed not exist domain,
            # but email_validator check this domain as invalid by default.
            # Using test_environment param for validate_email() an unnecessary
            # complication, we put it as is.
            ('username@not-exist-domain.ru', SUCCESS),
            ('username@hostname', FAIL),
        ])
    def test_case(self, value, raise_context):
        with raise_context:
            EmailValidator()(value)


class TestDatatimeFormatValidator:
    SUCCESS = nullcontext()
    FAIL = pytest.raises(DatetimeFormatValidationError)

    @pytest.mark.parametrize(
        'value, raise_context', [
            (None, SUCCESS),
            ('2001-02-03', FAIL),
            ('2001-02-03T12', FAIL),
            ('2001-02-03T12:34', FAIL),
            ('2001-02-03T12:34:56', FAIL),
            ('2001-02-03T12:34:56Z', FAIL),
            ('2001-02-03T12:34:56.123456', FAIL),
            ('2001-02-03T12:34:56.123456+00:00', FAIL),
            ('2001-02-03 12:34:56.123456+00:00', FAIL),
            ('2001-02-03T12:34:56.123456Z', SUCCESS),
            ('2001-02-03T12:34:56.12Z', SUCCESS),
        ])
    def test_case(self, value, raise_context):
        with raise_context:
            DatetimeValidator()(value)


class TestSchemaValidator:
    SUCCESS = nullcontext()
    FAIL = pytest.raises(ValidationError)

    schema = {
        'type': 'string',
        'format': ''}

    @pytest.mark.parametrize(
        'field_format, value, raise_context', [
            ('regex', '(/d{1-5})[A-za-z]+', SUCCESS),
            ('regex', '(/d{1-5})[A-za-z]++', FAIL),
            ('date', '2001-02-03', SUCCESS),
            ('date', '2001-02-03Z', FAIL),
            ('uuid', '0e10248d-3701-4e0a-bc2a-b01c7bb0f7df', SUCCESS),
            ('uuid', '0e10248d-3701-4e0a-bc2a-b01c7bb0f7df1', FAIL),
            ('email', 'username@hostname.ru', SUCCESS),
            ('email', 'username@hostname', FAIL),
            ('date-time', '2001-02-03T12:34:56.123456Z', SUCCESS),
            ('date-time', '2001-02-03T12:34:56.123456', FAIL),
        ])
    def test_case(self, field_format, value, raise_context):
        self.schema['format'] = field_format
        with raise_context:
            schema_validator(self.schema).validate(value)
