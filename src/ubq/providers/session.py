"""Common interface for authenticated provider sessions."""

from typing import Protocol, runtime_checkable

from ubq.models import AuthScope
from ubq.providers.bug import BugProvider
from ubq.providers.merge_request import MergeRequestProvider
from ubq.providers.package import PackageProvider
from ubq.providers.version import VersionProvider


@runtime_checkable
class ProviderSession(Protocol):
    """Authenticated provider session scoped by read-only or rw permissions."""

    provider_name: str
    scope: AuthScope

    def get_bug_provider(self) -> "BugProvider | None":
        """Return bug capability for this session if available."""
        ...

    def get_version_provider(self) -> "VersionProvider | None":
        """Return version capability for this session if available."""
        ...

    def get_package_provider(self) -> "PackageProvider | None":
        """Return package capability for this session if available."""
        ...

    def get_merge_request_provider(self) -> "MergeRequestProvider | None":
        """Return merge request capability for this session if available."""
        ...
