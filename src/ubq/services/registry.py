"""Registry of Ubuntu data providers."""

from typing import Iterable

from ubq.providers import (
    BugProvider,
    LaunchpadBugProvider,
    MergeRequestProvider,
    PackageProvider,
    Provider,
    VersionProvider,
)


class ProviderRegistry:
    """Registry of usable ubq data providers."""

    def __init__(self, providers: Iterable[Provider] | None = None):
        self._bug_providers: dict[str, BugProvider] = {}
        self._version_providers: dict[str, VersionProvider] = {}
        self._package_providers: dict[str, PackageProvider] = {}
        self._merge_request_providers: dict[str, MergeRequestProvider] = {}
        initial_providers = providers or (LaunchpadBugProvider(),)

        for provider in initial_providers:
            self.register(provider)

    def register(self, provider: Provider) -> None:
        """Register a provider by its provider name and capability."""
        key = provider.provider_name.lower()
        if isinstance(provider, BugProvider):
            self._bug_providers[key] = provider
        if isinstance(provider, VersionProvider):
            self._version_providers[key] = provider
        if isinstance(provider, PackageProvider):
            self._package_providers[key] = provider
        if isinstance(provider, MergeRequestProvider):
            self._merge_request_providers[key] = provider

    def get_bug_provider(self, provider_name: str) -> BugProvider:
        """Return bug provider for the given provider name."""
        return self._get_from_map(provider_name, self._bug_providers, "bug")

    def get_version_provider(self, provider_name: str) -> VersionProvider:
        """Return version provider for the given provider name."""
        return self._get_from_map(provider_name, self._version_providers, "version")

    def get_package_provider(self, provider_name: str) -> PackageProvider:
        """Return package provider for the given provider name."""
        return self._get_from_map(provider_name, self._package_providers, "package")

    def get_merge_request_provider(self, provider_name: str) -> MergeRequestProvider:
        """Return merge request provider for the given provider name."""
        return self._get_from_map(
            provider_name,
            self._merge_request_providers,
            "merge request",
        )

    def available_provider_names(self) -> tuple[str, ...]:
        """List all provider names with at least one registered capability."""
        names = {
            *self._bug_providers,
            *self._version_providers,
            *self._package_providers,
            *self._merge_request_providers,
        }
        return tuple(sorted(names))

    @staticmethod
    def _get_from_map(
        provider_name: str,
        providers: dict[str, Provider],
        capability_name: str,
    ) -> Provider:
        """Return provider for the specific capability map."""
        key = provider_name.lower()
        provider = providers.get(key)
        if provider is None:
            available = ", ".join(sorted(providers))
            raise ValueError(
                "Provider "
                f"'{provider_name}' does not support {capability_name}. "
                f"Available providers: {available}"
            )
        return provider
