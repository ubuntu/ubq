"""Common interface for all data providers."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Provider(Protocol):
    """Base ubq provider class."""

    provider_name: str
