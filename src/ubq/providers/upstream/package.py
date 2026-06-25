"""Upstream package data provider."""

from ubq.models import PackageRecord
from ubq.providers.package import PackageProvider
from ubq.providers.upstream.provider import UpstreamProvider


class UpstreamPackageProvider(UpstreamProvider, PackageProvider):
    """Provider implementation for upstream package locations."""

    def get_package(self, package_name: str, archive: str) -> PackageRecord | None:
        """Return the upstream project location for a package."""
        source = self._get_source(package_name)
        if source is None:
            return None
        return PackageRecord(
            provider_name=self.provider_name,
            name=package_name,
            archive=archive,
            package_url=source.project_url or source.stable_url,
        )
