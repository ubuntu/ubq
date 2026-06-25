"""Upstream package version provider."""

from ubq.models import VersionRecord
from ubq.providers.upstream.handlers import get_handler
from ubq.providers.upstream.provider import UpstreamProvider
from ubq.providers.version import VersionProvider


class UpstreamVersionProvider(UpstreamProvider, VersionProvider):
    """Provider implementation for latest upstream package versions."""

    def get_version(
        self, package_name: str, archive: str, series: str, pocket: str | None
    ) -> VersionRecord | None:
        """Fetch the latest upstream version of a package.

        ``series`` and ``pocket`` are echoed through but ignored: upstream
        sources have no notion of an Ubuntu series or pocket.
        """
        source = self._get_source(package_name)
        if source is None:
            return None
        version = get_handler(source.type).fetch_version(source, self._fetch_context)
        if version is None:
            return None
        return VersionRecord(
            provider_name=self.provider_name,
            version_string=version,
            package_name=package_name,
            archive=archive,
            series=series,
            pocket=pocket,
            changelog=None,
        )
