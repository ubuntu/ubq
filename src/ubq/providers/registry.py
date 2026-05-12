"""Registry and session manager for Ubuntu data providers."""

from collections.abc import Callable, Iterable

from ubq.models import AuthContext, AuthScope, ProviderCredentials
from ubq.providers.bug import BugProvider
from ubq.providers.github.bug import GitHubBugProvider
from ubq.providers.github.merge_request import GitHubMergeRequestProvider
from ubq.providers.launchpad.bug import LaunchpadBugProvider
from ubq.providers.launchpad.merge_request import LaunchpadMergeRequestProvider
from ubq.providers.launchpad.package import LaunchpadPackageProvider
from ubq.providers.launchpad.version import LaunchpadVersionProvider
from ubq.providers.merge_request import MergeRequestProvider
from ubq.providers.package import PackageProvider
from ubq.providers.provider import Provider
from ubq.providers.session import ProviderSession
from ubq.providers.version import VersionProvider


class ProviderRegistry:
    """Registry of providers and their authenticated sessions."""

    def __init__(
        self,
        providers: Iterable[Provider] | None = None,
    ):
        self._providers: dict[str, list[Provider]] = {}
        self._sessions: dict[tuple[str, AuthScope], ProviderSession] = {}
        initial_providers = providers or (
            GitHubBugProvider(),
            GitHubMergeRequestProvider(),
            LaunchpadBugProvider(),
            LaunchpadPackageProvider(),
            LaunchpadVersionProvider(),
            LaunchpadMergeRequestProvider(),
        )

        for provider in initial_providers:
            self.register(provider)

    def register(self, provider: Provider) -> None:
        """Register a provider by provider name."""
        key = provider.provider_name.lower()
        self._providers.setdefault(key, []).append(provider)

    def login(
        self,
        provider_name: str,
        scope: AuthScope = AuthScope.READ_ONLY,
        credentials: ProviderCredentials | None = None,
        force: bool = False,
    ) -> ProviderSession:
        """Authenticate with a provider and cache the scoped session."""
        key = (provider_name.lower(), scope)
        if not force:
            existing = self._sessions.get(key)
            if existing is not None:
                return existing

        providers = self._get_providers(provider_name)
        auth_context = AuthContext(
            provider_name=providers[0].provider_name,
            scope=scope,
            credentials=credentials,
        )
        session = providers[0].authenticate(auth_context)
        for provider in providers[1:]:
            session = session.with_provider(provider)
        self._sessions[key] = session
        return session

    def get_session(
        self,
        provider_name: str,
        scope: AuthScope = AuthScope.READ_ONLY,
    ) -> ProviderSession:
        """Get an existing scoped session for the provider."""
        key = (provider_name.lower(), scope)
        session = self._sessions.get(key)
        if session is None:
            raise ValueError(
                "No active session for provider "
                f"'{provider_name}' with scope '{scope.value}'. "
                "Call login() first."
            )
        return session

    def get_bug_provider(
        self,
        provider_name: str,
        scope: AuthScope = AuthScope.READ_ONLY,
    ) -> BugProvider:
        """Return bug provider for an active scoped session."""
        capability = self._capability_from_session(
            provider_name,
            scope,
            "bug",
            lambda session: session.get_bug_provider(),
        )

        if not isinstance(capability, BugProvider):
            raise ValueError("The capability returned is not a BugProvider.")

        return capability

    def get_version_provider(
        self,
        provider_name: str,
        scope: AuthScope = AuthScope.READ_ONLY,
    ) -> VersionProvider:
        """Return version provider for an active scoped session."""
        capability = self._capability_from_session(
            provider_name,
            scope,
            "version",
            lambda session: session.get_version_provider(),
        )

        if not isinstance(capability, VersionProvider):
            raise ValueError("The capability returned is not a VersionProvider.")

        return capability

    def get_package_provider(
        self,
        provider_name: str,
        scope: AuthScope = AuthScope.READ_ONLY,
    ) -> PackageProvider:
        """Return package provider for an active scoped session."""
        capability = self._capability_from_session(
            provider_name,
            scope,
            "package",
            lambda session: session.get_package_provider(),
        )

        if not isinstance(capability, PackageProvider):
            raise ValueError("The capability returned is not a PackageProvider.")

        return capability

    def get_merge_request_provider(
        self,
        provider_name: str,
        scope: AuthScope = AuthScope.READ_ONLY,
    ) -> MergeRequestProvider:
        """Return merge request provider for an active scoped session."""
        capability = self._capability_from_session(
            provider_name,
            scope,
            "merge request",
            lambda session: session.get_merge_request_provider(),
        )

        if not isinstance(capability, MergeRequestProvider):
            raise ValueError("The capability returned is not a MergeRequestProvider.")

        return capability

    def available_provider_names(self) -> tuple[str, ...]:
        """List all registered provider names."""
        return tuple(sorted(self._providers))

    def active_sessions(self) -> tuple[tuple[str, AuthScope], ...]:
        """List active provider sessions by provider and scope."""
        return tuple(sorted(self._sessions))

    def clear_session(
        self,
        provider_name: str,
        scope: AuthScope = AuthScope.READ_ONLY,
    ) -> None:
        """Clear a cached provider session."""
        self._sessions.pop((provider_name.lower(), scope), None)

    def _get_providers(self, provider_name: str) -> list[Provider]:
        """Return registered providers for the given provider name."""
        key = provider_name.lower()
        providers = self._providers.get(key)
        if not providers:
            available = ", ".join(sorted(self._providers))
            raise ValueError(
                f"Unknown provider '{provider_name}'. Available providers: {available}"
            )
        return providers

    def _capability_from_session(
        self,
        provider_name: str,
        scope: AuthScope,
        capability_name: str,
        getter: Callable[[ProviderSession], Provider | None],
    ) -> Provider:
        """Return capability from an active session or raise error."""
        session = self.get_session(provider_name, scope)
        capability = getter(session)
        if capability is None:
            raise ValueError(
                f"Provider '{provider_name}' does not support "
                f"{capability_name} queries for scope '{scope.value}'."
            )
        return capability
