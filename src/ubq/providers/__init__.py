"""Provider interfaces and implementations."""

from ubq.providers.bug import BugProvider
from ubq.providers.launchpad.bug import LaunchpadBugProvider
from ubq.providers.merge_request import MergeRequestProvider
from ubq.providers.package import PackageProvider
from ubq.providers.provider import Provider
from ubq.providers.version import VersionProvider

__all__ = [
    "Provider",
    "BugProvider",
    "PackageProvider",
    "VersionProvider",
    "MergeRequestProvider",
    "LaunchpadBugProvider",
]
