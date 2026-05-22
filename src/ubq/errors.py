"""Custom exceptions for the ubq package."""


class RequestTimeoutError(Exception):
    """Raised when a data request to a provider times out."""

    def __init__(self, provider_name: str, timeout: int) -> None:
        super().__init__(
            f"Request to provider '{provider_name}' timed out after {timeout} seconds."
        )
        self.provider_name = provider_name
        self.timeout = timeout
