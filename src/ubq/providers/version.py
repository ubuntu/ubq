"""Common interface for version data providers."""

from typing import runtime_checkable

from ubq.models import VersionRecord
from ubq.providers.provider import Provider


@runtime_checkable
class VersionProvider(Provider):
    """Contract that all version providers must implement."""

    def get_version(self, package_name: str, pocket: str) -> VersionRecord:
        """Fetch the version of a package by name and release pocket."""
        ...
