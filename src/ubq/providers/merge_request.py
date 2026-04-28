"""Common interface for merge request data providers."""

from typing import runtime_checkable

from ubq.models import MergeRequestRecord
from ubq.providers.provider import Provider


@runtime_checkable
class MergeRequestProvider(Provider):
    """Contract that all merge request providers must implement."""

    def get_merge_request(self, merge_request_id: str) -> MergeRequestRecord:
        """Fetch a merge request by provider-specific identifier."""
