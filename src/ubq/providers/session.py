"""Common interface for authenticated provider sessions."""

from dataclasses import dataclass, replace

from ubq.models import AuthScope
from ubq.providers.bug import BugProvider
from ubq.providers.merge_request import MergeRequestProvider
from ubq.providers.package import PackageProvider
from ubq.providers.version import VersionProvider


@dataclass(frozen=True, slots=True)
class ProviderSession:
    """Authenticated provider session scoped by read-only or rw permissions."""

    provider_name: str
    scope: AuthScope
    bug_provider: BugProvider | None = None
    version_provider: VersionProvider | None = None
    package_provider: PackageProvider | None = None
    merge_request_provider: MergeRequestProvider | None = None

    def with_provider(self, provider: object) -> "ProviderSession":
        """Return a new session with any supported capabilities attached."""
        session = self
        if isinstance(provider, BugProvider):
            session = replace(session, bug_provider=provider)
        if isinstance(provider, VersionProvider):
            session = replace(session, version_provider=provider)
        if isinstance(provider, PackageProvider):
            session = replace(session, package_provider=provider)
        if isinstance(provider, MergeRequestProvider):
            session = replace(session, merge_request_provider=provider)
        return session

    def get_bug_provider(self) -> BugProvider | None:
        """Return bug capability for this session if available."""
        return self.bug_provider

    def get_version_provider(self) -> VersionProvider | None:
        """Return version capability for this session if available."""
        return self.version_provider

    def get_package_provider(self) -> PackageProvider | None:
        """Return package capability for this session if available."""
        return self.package_provider

    def get_merge_request_provider(self) -> MergeRequestProvider | None:
        """Return merge request capability for this session if available."""
        return self.merge_request_provider
