"""Launchpad bug data provider."""

from typing import Any

from lazr.restfulclient.errors import NotFound  # type: ignore[import-untyped]

from ubq.models import BugRecord, BugTaskRecord, CommentRecord, UserRecord
from ubq.providers.bug import BugProvider
from ubq.providers.launchpad.provider import LaunchpadProvider

BASE_BUG_URL = "https://api.launchpad.net/devel/ubuntu/+bug/"
BASE_USER_URL = "https://launchpad.net/~"


class LaunchpadBugProvider(LaunchpadProvider, BugProvider):
    """Provider implementation for Launchpad bugs."""

    def _fetch_lp_bug_by_id(self, bug_id: str) -> Any:
        """Load a Launchpad URL and attempt to convert it to arbitrary bug data."""
        if self._launchpad is None:
            raise RuntimeError("Launchpad not yet authenticated. Run 'authenticate()' first.")

        try:
            lp_object = self._launchpad.load(BASE_BUG_URL + bug_id)
        except NotFound:
            return None

        # Launchpad will sometimes return default bug_task for a bug, if so it needs to be
        # converted to a bug explicitly. Otherwise assume it's already a bug.
        try:
            lp_bug = lp_object.bug
        except AttributeError:
            lp_bug = lp_object

        return lp_bug

    def get_bug_task_by_url(self, task_url: str) -> "BugTaskRecord | None":
        """Fetch a Launchpad bug task by URL."""
        if self._launchpad is None:
            raise RuntimeError("Launchpad not yet authenticated. Run 'authenticate()' first.")

        try:
            lp_task = self._launchpad.load(task_url)
        except NotFound:
            return None

        assignee = None
        if hasattr(lp_task, "assignee"):
            assignee = UserRecord(
                username=lp_task.assignee.name,
                display_name=lp_task.assignee.display_name,
                profile_url=f"{BASE_USER_URL}{lp_task.assignee.name}",
            )

        return BugTaskRecord(
            title=lp_task.title,
            target=lp_task.target,
            importance=lp_task.importance,
            status=lp_task.status,
            date_assigned=lp_task.date_assigned,
            date_closed=lp_task.date_closed,
            date_created=lp_task.date_created,
            date_left_closed=lp_task.date_left_closed,
            date_left_new=lp_task.date_left_new,
            date_incomplete=lp_task.date_incomplete,
            date_confirmed=lp_task.date_confirmed,
            date_triaged=lp_task.date_triaged,
            date_in_progress=lp_task.date_in_progress,
            date_fix_committed=lp_task.date_fix_committed,
            date_fix_released=lp_task.date_fix_released,
            milestone=lp_task.milestone.name if lp_task.milestone else None,
            assignee=assignee,
        )

    def get_bug_metadata(self, bug_id: str) -> "BugRecord | None":
        """Fetch a Launchpad bug without comments or tasks."""
        lp_bug = self._fetch_lp_bug_by_id(bug_id)
        if lp_bug is None:
            return None

        return BugRecord(
            provider_name=self.provider_name,
            id=str(lp_bug.id),
            title=lp_bug.title,
            description=lp_bug.description,
            created_at=lp_bug.date_created,
            updated_at=lp_bug.date_last_updated,
            last_message_at=lp_bug.date_last_message,
            last_patch_at=lp_bug.latest_patch_uploaded,
            tags=lp_bug.tags,
        )

    def get_bug(self, bug_id: str) -> "BugRecord | None":
        """Fetch a Launchpad bug by identifier."""
        lp_bug = self._fetch_lp_bug_by_id(bug_id)
        if lp_bug is None:
            return None

        tasks: list["BugTaskRecord"] = []
        if hasattr(lp_bug, "bug_tasks"):
            for task in lp_bug.bug_tasks:
                task_record = self.get_bug_task_by_url(str(task))
                if task_record is not None:
                    tasks.append(task_record)

        comments: list["CommentRecord"] = []
        if hasattr(lp_bug, "messages"):
            for msg in lp_bug.messages:
                if msg.visible:
                    author = None
                    if hasattr(msg, "owner") and msg.owner is not None:
                        author = UserRecord(
                            username=msg.owner.name,
                            display_name=msg.owner.display_name,
                            profile_url=f"{BASE_USER_URL}{msg.owner.name}",
                        )

                    comments.append(
                        CommentRecord(
                            author=author,
                            content=msg.content,
                            created_at=msg.date_created,
                            edited_at=msg.date_last_edited,
                        )
                    )

        return BugRecord(
            provider_name=self.provider_name,
            id=str(lp_bug.id),
            title=lp_bug.title,
            description=lp_bug.description,
            created_at=lp_bug.date_created,
            updated_at=lp_bug.date_last_updated,
            last_message_at=lp_bug.date_last_message,
            last_patch_at=lp_bug.latest_patch_uploaded,
            tags=lp_bug.tags,
            bug_tasks=tasks,
            comments=comments,
        )
