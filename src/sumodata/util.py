"""Common utilities and exception classes."""


class SumodataError(Exception):
    """Base exception for sumodata."""


class FetchError(SumodataError):
    """HTTP fetch failure after retries."""


class ParseError(SumodataError):
    """HTML parse failure."""
