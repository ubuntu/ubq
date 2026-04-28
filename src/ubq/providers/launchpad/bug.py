"""Launchpad bug data provider."""

from ubq.models import BugRecord
from ubq.providers.bug import BugProvider
from ubq.providers.launchpad.provider import LaunchpadProvider


class LaunchpadBugProvider(LaunchpadProvider, BugProvider):
    """Provider implementation for Launchpad bugs."""

    def get_bug(self, bug_id: str) -> BugRecord:
        """Fetch a Launchpad bug by identifier."""
