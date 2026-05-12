"""Provider interfaces and implementations."""

from ubq.providers.bug import BugProvider
from ubq.providers.github.bug import GitHubBugProvider
from ubq.providers.github.merge_request import GitHubMergeRequestProvider
from ubq.providers.github.provider import GitHubProvider
from ubq.providers.launchpad.bug import LaunchpadBugProvider
from ubq.providers.launchpad.merge_request import LaunchpadMergeRequestProvider
from ubq.providers.launchpad.package import LaunchpadPackageProvider
from ubq.providers.launchpad.version import LaunchpadVersionProvider
from ubq.providers.merge_request import MergeRequestProvider
from ubq.providers.package import PackageProvider
from ubq.providers.provider import Provider
from ubq.providers.registry import ProviderRegistry
from ubq.providers.session import ProviderSession
from ubq.providers.snapcraft.package import SnapcraftPackageProvider
from ubq.providers.snapcraft.provider import SnapcraftProvider
from ubq.providers.snapcraft.version import SnapcraftVersionProvider
from ubq.providers.version import VersionProvider

__all__ = [
    "Provider",
    "ProviderRegistry",
    "ProviderSession",
    "BugProvider",
    "PackageProvider",
    "VersionProvider",
    "MergeRequestProvider",
    "GitHubProvider",
    "GitHubBugProvider",
    "GitHubMergeRequestProvider",
    "LaunchpadBugProvider",
    "LaunchpadMergeRequestProvider",
    "LaunchpadPackageProvider",
    "LaunchpadVersionProvider",
    "SnapcraftProvider",
    "SnapcraftPackageProvider",
    "SnapcraftVersionProvider",
]
