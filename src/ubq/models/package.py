"""Package model records."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PackageRecord:
    """Package metadata in a provider."""

    provider_name: str
    name: str
    package_url: str | None = None
