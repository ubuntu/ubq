"""Get deb package versions from Launchpad."""

import urllib.error
import urllib.request

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
        self, package_name: str, archive: str, series: str, pocket: str | None
    ) -> VersionRecord | None:
        """Fetch the latest version of a package by name, series and release pocket."""

        if pocket is None or pocket not in VALID_LP_POCKETS:
            raise ValueError(
                f"Invalid Ubuntu pocket: '{pocket}'."
                f" Valid pockets are: {', '.join(VALID_LP_POCKETS)}."
            )

        try:
            distro = self._get_distro_object(archive)

            lp_archive = getattr(distro, "main_archive", None)
            if lp_archive is None:
                return None
            lp_series = distro.getSeries(name_or_version=series)

            sources = lp_archive.getPublishedSources(
                exact_match=True,
                order_by_date=True,
                source_name=package_name,
                distro_series=lp_series,
                pocket=pocket,
                status="Published",
            )

            if sources is not None and len(sources) > 0:
                latest_source = sources[0]

                changelog = ""
                if hasattr(latest_source, "changelogUrl"):
                    changelog_url = latest_source.changelogUrl()
                    if changelog_url:
                        try:
                            with urllib.request.urlopen(
                                changelog_url, timeout=self._timeout
                            ) as resp:
                                changelog = resp.read().decode("utf-8", errors="replace")
                        except urllib.error.URLError as exc:
                            if isinstance(exc.reason, TimeoutError):
                                raise self._wrap_timeout(exc) from exc
                            raise

                version_string = getattr(latest_source, "source_package_version", None)
                package_name = getattr(latest_source, "source_package_name", None)
                if version_string is None or package_name is None:
                    return None

                return VersionRecord(
                    provider_name=self.provider_name,
                    version_string=version_string,
                    package_name=package_name,
                    archive=archive,
                    series=series,
                    pocket=pocket,
                    created_at=getattr(latest_source, "date_created", None),
                    released_at=getattr(latest_source, "date_published", None),
                    changelog=changelog,
                )

            return None
        except TimeoutError as exc:
            raise self._wrap_timeout(exc) from exc
