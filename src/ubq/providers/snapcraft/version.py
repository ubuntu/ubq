"""Snapcraft package version provider."""

from datetime import datetime, timezone

from ubq.models import VersionRecord
from ubq.providers.snapcraft.provider import SnapcraftProvider
from ubq.providers.version import VersionProvider


class SnapcraftVersionProvider(SnapcraftProvider, VersionProvider):
    """Provider implementation for Snapcraft snap versions.

    The ``series`` parameter is the channel track (e.g. ``latest``, ``1.0``).
    The ``pocket`` parameter is the risk level after the ``/`` separator
    (e.g. ``stable``, ``candidate``, ``beta``, ``edge``).

    For example, the channel ``latest/stable`` has series ``latest`` and
    pocket ``stable``. If only a full channel name is known (e.g. ``latest/stable``)
    it can be passed as ``series`` with ``pocket=None``.
    """

    def get_version(
        self, package_name: str, series: str, pocket: str | None
    ) -> VersionRecord | None:
        """Fetch the current version of a snap for a given track and risk level."""
        data = self._rest_get(
            f"/snaps/info/{package_name}",
            params={"fields": "name,version,channel-map"},
        )

        snap_name = data.get("name", package_name)
        channel_map = data.get("channel-map", [])

        for entry in channel_map:
            channel = entry.get("channel", {})
            if pocket is not None:
                match = channel.get("track") == series and channel.get("risk") == pocket
            else:
                match = channel.get("name") == series

            if not match:
                continue

            version_string = entry.get("version")
            if version_string is None:
                continue

            released_at: datetime | None = None
            released_at_raw = channel.get("released-at")
            if released_at_raw:
                try:
                    released_at = datetime.fromisoformat(released_at_raw).replace(
                        tzinfo=timezone.utc
                    )
                except ValueError:
                    pass

            return VersionRecord(
                provider_name=self.provider_name,
                version_string=version_string,
                package_name=snap_name,
                series=series,
                pocket=pocket,
                released_at=released_at,
            )

        return None
