class APIError(Exception):
    """Base class for API exceptions."""
    pass


class InvalidResponseError(APIError):
    """Raised when API returns an invalid response."""
    pass


class APILimitExceededError(APIError):
    """Raised when API rate limits are exceeded."""
    pass
