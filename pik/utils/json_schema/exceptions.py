class BaseFormatValidationError(Exception):
    pass


class DatetimeFormatValidationError(BaseFormatValidationError):
    pass


class EmailFormatValidationError(BaseFormatValidationError):
    pass
