"""Version model records."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class VersionRecord:
    """Version information for a package in a provider."""

    provider_name: str
    version_string: str
    package_name: str
    series: str | None = None
    pocket: str | None = None
    created_at: datetime | None = None
    released_at: datetime | None = None
