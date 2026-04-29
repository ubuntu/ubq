"""Launchpad package data provider."""

from ubq.models import PackageRecord
from ubq.providers.launchpad.provider import LaunchpadProvider
from ubq.providers.package import PackageProvider


class LaunchpadPackageProvider(LaunchpadProvider, PackageProvider):
    """Provider implementation for Launchpad packages."""

    def get_package(self, package_name: str) -> "PackageRecord | None":
        """Fetch a Launchpad package by name."""
