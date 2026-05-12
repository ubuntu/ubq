"""GitHub data provider implementations."""

from ubq.providers.github.bug import GitHubBugProvider
from ubq.providers.github.merge_request import GitHubMergeRequestProvider
from ubq.providers.github.provider import GitHubProvider

__all__ = [
    "GitHubProvider",
    "GitHubBugProvider",
    "GitHubMergeRequestProvider",
]
