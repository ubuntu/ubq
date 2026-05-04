"""Common interface for version data providers."""

from typing import Protocol, runtime_checkable

from ubq.models import VersionRecord
from ubq.providers.provider import Provider


@runtime_checkable
class VersionProvider(Provider, Protocol):
    """Contract that all version providers must implement."""

    def get_version(self, package_name: str, series: str, pocket: str) -> VersionRecord | None:
        """Fetch the version of a package by name and release pocket."""
