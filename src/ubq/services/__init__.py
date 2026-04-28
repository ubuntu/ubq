"""Service entry points for querying data providers."""

from ubq.services.query import QueryService
from ubq.services.registry import ProviderRegistry

__all__ = [
    "QueryService",
    "ProviderRegistry",
]
