"""Common interface for merge request data providers."""

from typing import Protocol, runtime_checkable

from ubq.models import MergeRequestRecord
from ubq.providers.provider import Provider


@runtime_checkable
class MergeRequestProvider(Provider, Protocol):
    """Contract that all merge request providers must implement."""

    def get_merge_request(self, merge_request_id: str) -> "MergeRequestRecord | None":
        """Fetch a merge request by provider-specific identifier."""
