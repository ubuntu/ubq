"""Query service for Ubuntu data."""

from ubq.models import BugRecord, MergeRequestRecord, PackageRecord, VersionRecord
from ubq.services.registry import ProviderRegistry


class QueryService:
    """Query facade that dispatches requests to a selected provider."""

    def __init__(self, registry: ProviderRegistry | None = None):
        self._registry = registry or ProviderRegistry()

    def get_bug(self, bug_id: str, provider_name: str) -> BugRecord:
        """Fetch a bug from a specific provider by provider name."""
        provider = self._registry.get_bug_provider(provider_name)
        return provider.get_bug(bug_id)

    def get_version(self, version_id: str, provider_name: str) -> VersionRecord:
        """Fetch a version from a specific provider by provider name."""
        provider = self._registry.get_version_provider(provider_name)
        return provider.get_version(version_id)

    def get_package(self, package_id: str, provider_name: str) -> PackageRecord:
        """Fetch a package from a specific provider by provider name."""
        provider = self._registry.get_package_provider(provider_name)
        return provider.get_package(package_id)

    def get_merge_request(
        self,
        merge_request_id: str,
        provider_name: str,
    ) -> MergeRequestRecord:
        """Fetch a merge request from a specific provider by provider name."""
        provider = self._registry.get_merge_request_provider(provider_name)
        return provider.get_merge_request(merge_request_id)

    def available_providers(self) -> tuple[str, ...]:
        """Return all provider names queryable by this service."""
        return self._registry.available_provider_names()
