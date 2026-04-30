"""Common interface for bug data providers."""

from typing import Protocol, runtime_checkable

from ubq.models import BugRecord, BugSubmissionRecord
from ubq.providers.provider import Provider


@runtime_checkable
class BugProvider(Provider, Protocol):
    """Contract that all bug providers must implement."""

    def get_bug_metadata(self, bug_id: str) -> "BugRecord | None":
        """Fetch a single bug without additional requests for comments or tasks."""

    def get_bug(self, bug_id: str) -> "BugRecord | None":
        """Fetch a single bug by provider-specific identifier."""

    def submit_bug(self, submission: BugSubmissionRecord) -> "BugRecord | None":
        """Submit a new bug to the provider and return the created record."""
