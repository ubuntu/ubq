"""Launchpad bug data provider."""

from typing import Any

from lazr.restfulclient.errors import NotFound  # type: ignore[import-untyped]

from ubq.models import BugRecord, BugSubmissionRecord, BugTaskRecord, CommentRecord, UserRecord
from ubq.providers.bug import BugProvider
from ubq.providers.launchpad.provider import LaunchpadProvider

BASE_USER_URL = "https://launchpad.net/~"
VALID_BUG_STATUSES = {
    "New",
    "Incomplete",
    "Opinion",
    "Invalid",
    "Won\\'t Fix",
    "Expired",
    "Confirmed",
    "Triaged",
    "In Progress",
    "Deferred",
    "Fix Committed",
    "Fix Released",
    "Does Not Exist",
    "Unknown",
}

VALID_BUG_IMPORTANCES = {
    "Unknown",
    "Undecided",
    "Critical",
    "High",
    "Medium",
    "Low",
    "Wishlist",
}


class LaunchpadBugProvider(LaunchpadProvider, BugProvider):
    """Provider implementation for Launchpad bugs."""

    def _fetch_lp_bug_by_id(self, bug_id: str) -> Any:
        """Load a Launchpad URL and attempt to convert it to arbitrary bug data."""
        self._check_authenticated()

        try:
            return self._launchpad.bugs[bug_id]
        except KeyError:
            return None

    def _validate_bug_submission(self, submission: BugSubmissionRecord) -> None:
        """Validate a bug submission record and raise ValueError if invalid."""
        if len(submission.package_names) == 0:
            raise ValueError("At least one Ubuntu package must be specified for bug submission.")

        if submission.status is not None and submission.status not in VALID_BUG_STATUSES:
            raise ValueError(f"Invalid bug status provided: '{submission.status}'.")

        if (
            submission.importance is not None
            and submission.importance not in VALID_BUG_IMPORTANCES
        ):
            raise ValueError(f"Invalid bug importance provided: '{submission.importance}'.")

    def get_bug_task_by_url(self, task_url: str) -> "BugTaskRecord | None":
        """Fetch a Launchpad bug task by URL."""
        self._check_authenticated()

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

    def submit_bug(self, submission: BugSubmissionRecord) -> "BugRecord | None":
        """Submit a new bug to Launchpad and return the created record."""
        self._check_authenticated()
        self._validate_bug_submission(submission)

        first_package = self._get_lp_source_package_object(submission.package_names[0])
        if first_package is None:
            raise ValueError(f"Package '{submission.package_names[0]}' not found in Launchpad.")

        # Submit bug against the first package
        created_lp_bug = self._launchpad.bugs.createBug(
            title=submission.title,
            description=submission.description or "",
            target=first_package,
            tags=submission.tags,
            information_type="Private" if submission.private else "Public",
            private=submission.private,
        )

        # Add all other affected packages
        for pkg_name in submission.package_names[1:]:
            lp_package = self._get_lp_source_package_object(pkg_name)
            if lp_package is None:
                raise ValueError(f"Package '{pkg_name}' not found in Launchpad.")
            created_lp_bug.addTask(target=lp_package)

        lp_milestone = None
        if submission.milestone is not None:
            lp_milestone = self._launchpad.distributions["ubuntu"].getMilestone(
                name=submission.milestone
            )

        lp_owner = None
        if submission.assignee is not None:
            lp_owner = self._launchpad.people[submission.assignee.username]

        # Set milestone, status, and importance for each task if specified
        # Also fill out the task list for this bug as they are collected
        bug_task_list: list[BugTaskRecord] = []

        for lp_task in created_lp_bug.bug_tasks:
            if lp_milestone is not None:
                lp_task.milestone = lp_milestone

            if submission.status is not None:
                lp_task.status = submission.status

            if submission.importance is not None:
                lp_task.importance = submission.importance

            if lp_owner is not None:
                lp_task.owner = lp_owner

            lp_task.lp_save()
            bug_task_list.append(
                BugTaskRecord(
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
                    assignee=submission.assignee,
                )
            )

        # Add subscribers
        for subscriber in submission.subscribers:
            created_lp_bug.subscribe(person=subscriber.username)

        return BugRecord(
            provider_name=self.provider_name,
            id=str(created_lp_bug.id),
            title=created_lp_bug.title,
            description=created_lp_bug.description,
            created_at=created_lp_bug.date_created,
            updated_at=created_lp_bug.date_last_updated,
            last_message_at=created_lp_bug.date_last_message,
            last_patch_at=created_lp_bug.latest_patch_uploaded,
            tags=created_lp_bug.tags,
            bug_tasks=bug_task_list,
        )
