"""Launchpad bug data provider."""

from ubq.models import BugRecord
from ubq.providers.bug import BugProvider


class LaunchpadBugProvider(BugProvider):
    """Provider implementation for Launchpad bugs."""

    provider_name = "launchpad"

    def get_bug(self, bug_id: str) -> BugRecord:
        """Fetch a Launchpad bug by identifier."""
        ...
