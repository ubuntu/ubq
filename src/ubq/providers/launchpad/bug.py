"""Launchpad bug data provider."""

from typing import Any

from lazr.restfulclient.errors import NotFound  # type: ignore[import-untyped]

from ubq.models import BugRecord, BugSubmissionRecord, BugTaskRecord, CommentRecord, UserRecord
from ubq.providers.bug import BugProvider
from ubq.providers.launchpad.provider import LP_BASE_USER_URL, LaunchpadProvider

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
        lp = self._get_lp_object()

        try:
            return lp.bugs[bug_id]
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

    def _add_bug_tasks(self, bug_id: str, submission: BugSubmissionRecord) -> list[BugTaskRecord]:
        """Add tasks to an existing Launchpad bug."""
        lp_bug = self._fetch_lp_bug_by_id(bug_id)
        if lp_bug is None:
            return []

        new_tasks: list[BugTaskRecord] = []
        for pkg_name in submission.package_names:
            lp_package = self._get_lp_source_package_object(pkg_name)
            if lp_package is None:
                raise ValueError(f"Package '{pkg_name}' not found in Launchpad.")
            new_lp_task = lp_bug.addTask(target=lp_package)

        lp_milestone = None
        if submission.milestone is not None:
            lp_milestone = self._get_lp_ubuntu_distro_object().getMilestone(
                name=submission.milestone
            )

        lp_assignee = None
        if submission.assignee is not None:
            lp_assignee = self._get_lp_object().people[submission.assignee.username]

        # Set owner, milestone, status, and importance for each new task if specified
        for lp_task in lp_bug.bug_tasks:
            if lp_milestone is not None:
                lp_task.milestone = lp_milestone

            if submission.status is not None:
                lp_task.status = submission.status

            if submission.importance is not None:
                lp_task.importance = submission.importance

            if lp_assignee is not None:
                lp_task.assignee = lp_assignee

            lp_task.lp_save()

            new_tasks.append(
                BugTaskRecord(
                    title=new_lp_task.title,
                    target=new_lp_task.target,
                    importance=new_lp_task.importance,
                    status=new_lp_task.status,
                    date_assigned=new_lp_task.date_assigned,
                    date_closed=new_lp_task.date_closed,
                    date_created=new_lp_task.date_created,
                    date_left_closed=new_lp_task.date_left_closed,
                    date_left_new=new_lp_task.date_left_new,
                    date_incomplete=new_lp_task.date_incomplete,
                    date_confirmed=new_lp_task.date_confirmed,
                    date_triaged=new_lp_task.date_triaged,
                    date_in_progress=new_lp_task.date_in_progress,
                    date_fix_committed=new_lp_task.date_fix_committed,
                    date_fix_released=new_lp_task.date_fix_released,
                    milestone=new_lp_task.milestone.name if new_lp_task.milestone else None,
                )
            )

        return new_tasks

    def get_bug_task_by_url(self, task_url: str) -> BugTaskRecord | None:
        """Fetch a Launchpad bug task by URL."""
        lp = self._get_lp_object()

        try:
            lp_task = lp.load(task_url)
        except NotFound:
            return None

        assignee = None
        if hasattr(lp_task, "assignee"):
            assignee_data = lp_task.assignee
            assignee = UserRecord(
                username=assignee_data.name,
                display_name=assignee_data.display_name,
                profile_url=f"{LP_BASE_USER_URL}{assignee_data.name}",
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

    def get_bug_metadata(self, bug_id: str) -> BugRecord | None:
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

    def get_bug(self, bug_id: str) -> BugRecord | None:
        """Fetch a Launchpad bug by identifier."""
        lp_bug = self._fetch_lp_bug_by_id(bug_id)
        if lp_bug is None:
            return None

        tasks: list[BugTaskRecord] = []
        if hasattr(lp_bug, "bug_tasks"):
            for task in lp_bug.bug_tasks:
                task_record = self.get_bug_task_by_url(str(task))
                if task_record is not None:
                    tasks.append(task_record)

        comments: list[CommentRecord] = []
        if hasattr(lp_bug, "messages"):
            for msg in lp_bug.messages:
                if msg.visible:
                    author = None
                    if hasattr(msg, "owner") and msg.owner is not None:
                        owner_data = msg.owner
                        author = UserRecord(
                            username=owner_data.name,
                            display_name=owner_data.display_name,
                            profile_url=f"{LP_BASE_USER_URL}{owner_data.name}",
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

    def submit_bug(self, submission: BugSubmissionRecord) -> BugRecord | None:
        """Submit a new bug to Launchpad and return the created record."""
        self._validate_bug_submission(submission)

        first_package = self._get_lp_source_package_object(submission.package_names[0])
        if first_package is None:
            raise ValueError(f"Package '{submission.package_names[0]}' not found in Launchpad.")

        # Submit bug against the first package
        created_lp_bug = self._get_lp_object().bugs.createBug(
            title=submission.title,
            description=submission.description or "",
            target=first_package,
            tags=submission.tags,
            information_type="Private" if submission.private else "Public",
            private=submission.private,
        )

        tasks = self._add_bug_tasks(str(created_lp_bug.id), submission)

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
            bug_tasks=tasks if tasks is not None else [],
        )
