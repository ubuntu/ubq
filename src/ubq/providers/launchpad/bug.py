"""Launchpad bug data provider."""

from lazr.restfulclient.resource import Entry

from ubq.models import BugRecord, UserRecord
from ubq.providers.bug import BugProvider
from ubq.providers.launchpad.provider import LaunchpadProvider

BASE_BUG_URL = "https://api.launchpad.net/devel/ubuntu/+bug/"


class LaunchpadBugProvider(LaunchpadProvider, BugProvider):
    """Provider implementation for Launchpad bugs."""

    def get_bug(self, bug_id: str) -> BugRecord:
        """Fetch a Launchpad bug by identifier."""
        if self._launchpad is None:
            raise RuntimeError("Launchpad not yet authenticated. Run 'authenticate()' first.")

        lp_object = self._launchpad.load(BASE_BUG_URL + bug_id)

        # Launchpad will sometimes return default bug_task for a bug, if so it needs to be
        # converted to a bug explicitly. Otherwise assume it's already a bug.
        try:
            lp_bug = lp_object.bug
        except AttributeError:
            lp_bug = lp_object

        return BugRecord(
            provider_name=self.provider_name,
            id=str(lp_bug.id),
            title=lp_bug.title,
            created_at=lp_bug.date_created,
        )
