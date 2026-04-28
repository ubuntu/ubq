"""Common interface for package data providers."""

from typing import runtime_checkable

from ubq.models import PackageRecord
from ubq.providers.provider import Provider


@runtime_checkable
class PackageProvider(Provider):
    """Contract that all package providers must implement."""

    def get_package(self, package_name: str) -> PackageRecord:
        """Fetch a single package by provider-specific name."""
        ...
