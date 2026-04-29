"""Query service for Ubuntu data."""

from ubq.models import (
    AuthScope,
    BugRecord,
    MergeRequestRecord,
    PackageRecord,
    ProviderCredentials,
    VersionRecord,
)
from ubq.services.registry import ProviderRegistry


class QueryService:
    """Query service for data from provider sessions."""

    def __init__(self, registry: ProviderRegistry | None = None):
        self._registry = registry or ProviderRegistry()

    def login(
        self,
        provider_name: str,
        scope: AuthScope = AuthScope.READ_ONLY,
        credentials: ProviderCredentials | None = None,
        force: bool = False,
    ) -> None:
        """Create or refresh a scoped provider session."""
        self._registry.login(
            provider_name=provider_name,
            scope=scope,
            credentials=credentials,
            force=force,
        )

    def get_bug(
        self,
        bug_id: str,
        provider_name: str,
        scope: AuthScope = AuthScope.READ_ONLY,
        metadata_only: bool = False,
    ) -> BugRecord:
        """Fetch a bug from a provider using an active scoped session."""
        provider = self._registry.get_bug_provider(provider_name, scope=scope)

        if metadata_only:
            return provider.get_bug_metadata(bug_id)

        return provider.get_bug(bug_id)

    def get_version(
        self,
        package_name: str,
        pocket: str,
        provider_name: str,
        scope: AuthScope = AuthScope.READ_ONLY,
    ) -> VersionRecord:
        """Fetch package version metadata using an active scoped session."""
        provider = self._registry.get_version_provider(provider_name, scope=scope)
        return provider.get_version(package_name, pocket)

    def get_package(
        self,
        package_name: str,
        provider_name: str,
        scope: AuthScope = AuthScope.READ_ONLY,
    ) -> PackageRecord:
        """Fetch a package from a provider using an active scoped session."""
        provider = self._registry.get_package_provider(provider_name, scope=scope)
        return provider.get_package(package_name)

    def get_merge_request(
        self,
        merge_request_id: str,
        provider_name: str,
        scope: AuthScope = AuthScope.READ_ONLY,
    ) -> MergeRequestRecord:
        """Fetch a merge request using an active scoped session."""
        provider = self._registry.get_merge_request_provider(provider_name, scope=scope)
        return provider.get_merge_request(merge_request_id)

    def available_providers(self) -> tuple[str, ...]:
        """Return all provider names queryable by this service."""
        return self._registry.available_provider_names()
