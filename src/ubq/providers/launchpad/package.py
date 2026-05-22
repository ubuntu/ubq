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
            pkg_name = getattr(source_package, "name", None)
            if pkg_name is None:
                return None

            return PackageRecord(
                provider_name=self.provider_name,
                name=pkg_name,
                archive=archive,
                package_url=getattr(source_package, "web_link", None),
            )
        except TimeoutError as exc:
            raise self._wrap_timeout(exc) from exc
