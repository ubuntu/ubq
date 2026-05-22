"""ubq — Ubuntu data query library."""

from ubq.errors import RequestTimeoutError
from ubq.query import QueryService

__all__ = [
    "QueryService",
    "RequestTimeoutError",
]
