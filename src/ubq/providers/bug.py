"""Common interface for bug data providers."""

from typing import runtime_checkable

from ubq.models import BugRecord
from ubq.providers.provider import Provider


@runtime_checkable
class BugProvider(Provider):
    """Contract that all bug providers must implement."""

    def get_bug(self, bug_id: str) -> BugRecord:
        """Fetch a single bug by provider-specific identifier."""
        ...
