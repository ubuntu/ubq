"""Launchpad package data provider."""

from ubq.models import PackageRecord
from ubq.providers.launchpad.provider import LaunchpadProvider
from ubq.providers.package import PackageProvider


class LaunchpadPackageProvider(LaunchpadProvider, PackageProvider):
    """Provider implementation for Launchpad packages."""

    def get_package(self, package_name: str) -> "PackageRecord | None":
        """Fetch a Launchpad package by name."""
        self._check_authenticated()

        source_package = self._launchpad.distributions["ubuntu"].getSourcePackage(
            name=package_name
        )

        if source_package is None:
            return None

        return PackageRecord(
            provider_name=self.provider_name,
            name=source_package.name,
            package_url=source_package.web_link,
        )
