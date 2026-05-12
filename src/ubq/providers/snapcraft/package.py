"""Snapcraft package data provider."""

from ubq.models import PackageRecord
from ubq.providers.package import PackageProvider
from ubq.providers.snapcraft.provider import SNAPCRAFT_STORE_BASE, SnapcraftProvider


class SnapcraftPackageProvider(SnapcraftProvider, PackageProvider):
    """Provider implementation for Snapcraft packages."""

    def get_package(self, package_name: str) -> PackageRecord | None:
        """Fetch a Snapcraft package by name."""
        data = self._rest_get(f"/snaps/info/{package_name}", params={"fields": "name,store-url"})

        name = data.get("name")
        if name is None:
            return None

        snap = data.get("snap", {})
        package_url = snap.get("store-url") or f"{SNAPCRAFT_STORE_BASE}/{name}"

        return PackageRecord(
            provider_name=self.provider_name,
            name=name,
            package_url=package_url,
        )
