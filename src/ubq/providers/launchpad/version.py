"""Get deb package versions from Launchpad."""

from ubq.models import VersionRecord
from ubq.providers.launchpad.provider import LaunchpadProvider
from ubq.providers.version import VersionProvider

VALID_LP_POCKETS = {
    "Release",
    "Updates",
    "Proposed",
    "Backports",
    "Security",
}


class LaunchpadVersionProvider(LaunchpadProvider, VersionProvider):
    """Provider implementation for Launchpad deb package versions."""

    def get_version(
        self, package_name: str, archive:str, series: str, pocket: str | None
    ) -> VersionRecord | None:
        """Fetch the latest version of a package by name, series and release pocket."""

        if pocket is None or pocket not in VALID_LP_POCKETS:
            raise ValueError(
                f"Invalid Ubuntu pocket: '{pocket}'."
                f" Valid pockets are: {', '.join(VALID_LP_POCKETS)}."
            )

        distro = self._get_distro_object(archive)

        archive = distro.main_archive
        series = distro.getSeries(name_or_version=series)

        sources = archive.getPublishedSources(
            exact_match=True,
            order_by_date=True,
            source_name=package_name,
            distro_series=series,
            pocket=pocket,
            status="Published",
        )

        if sources is not None and len(sources) > 0:
            latest_source = sources[0]
            return VersionRecord(
                provider_name=self.provider_name,
                version_string=latest_source.source_package_version,
                package_name=latest_source.source_package_name,
                archive=archive,
                series=series,
                pocket=pocket,
                created_at=latest_source.date_created,
                released_at=latest_source.date_published,
            )

        return None
