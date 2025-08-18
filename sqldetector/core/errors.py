class SQLDetectorError(BaseException):
    """Base class for sqldetector errors."""


class TimeoutError(SQLDetectorError):
    pass


class WAFBlocked(SQLDetectorError):
    pass


class ParseError(SQLDetectorError):
    pass


class PolicyViolation(SQLDetectorError):
    pass


class RetryBudgetExceeded(SQLDetectorError):
    pass
