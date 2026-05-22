"""Launchpad package data provider."""

from ubq.models import PackageRecord
from ubq.providers.launchpad.provider import LaunchpadProvider
from ubq.providers.package import PackageProvider


class LaunchpadPackageProvider(LaunchpadProvider, PackageProvider):
    """Provider implementation for Launchpad packages."""

    def get_package(self, package_name: str, archive: str) -> "PackageRecord | None":
        """Fetch a Launchpad package by name and archive."""
        source_package = self._get_lp_source_package_object(package_name, archive)

        if source_package is None:
            return None

        try:
            return PackageRecord(
                provider_name=self.provider_name,
                name=source_package.name,
                archive=archive,
                package_url=source_package.web_link,
            )
        except TimeoutError as exc:
            raise self._wrap_timeout(exc) from exc
