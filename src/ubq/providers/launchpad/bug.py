"""Launchpad bug data provider."""

from typing import Any

from lazr.restfulclient.errors import NotFound  # type: ignore[import-untyped]

from ubq.models import (
    BugRecord,
    BugSearchRecord,
    BugSubmissionRecord,
    BugTaskRecord,
    CommentRecord,
    UserRecord,
)
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
        except TimeoutError as exc:
            raise self._wrap_timeout(exc) from exc

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

        try:
            # Add new tasks, skipping the first package which was used for initial submission.
            new_tasks: list[BugTaskRecord] = []
            for pkg_name in submission.package_names[1:]:
                lp_package = self._get_lp_source_package_object(pkg_name, "ubuntu")
                if lp_package is None:
                    raise ValueError(f"Package '{pkg_name}' not found in Launchpad.")
                lp_bug.addTask(target=lp_package)

            lp_milestone = None
            if submission.milestone is not None:
                lp_milestone = self._get_distro_object("ubuntu").getMilestone(
                    name=submission.milestone
                )

            lp_assignee = None
            if submission.assignee is not None:
                lp_assignee = self._get_lp_object().people[submission.assignee.username]

            # Set owner, milestone, status, and importance for each new task if specified
            if not hasattr(lp_bug, "bug_tasks"):
                return new_tasks
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

                target = None
                package_name = None
                if hasattr(lp_task, "target"):
                    target = str(lp_task.target)
                    split_target = target.split("/")
                    if len(split_target) > 0:
                        package_name = split_target[-1]

                lp_task_milestone = getattr(lp_task, "milestone", None)
                new_tasks.append(
                    BugTaskRecord(
                        title=getattr(lp_task, "title", ""),
                        target=target,
                        package_name=package_name,
                        importance=getattr(lp_task, "importance", None),
                        status=getattr(lp_task, "status", None),
                        date_assigned=getattr(lp_task, "date_assigned", None),
                        date_closed=getattr(lp_task, "date_closed", None),
                        date_created=getattr(lp_task, "date_created", None),
                        date_left_closed=getattr(lp_task, "date_left_closed", None),
                        date_left_new=getattr(lp_task, "date_left_new", None),
                        date_incomplete=getattr(lp_task, "date_incomplete", None),
                        date_confirmed=getattr(lp_task, "date_confirmed", None),
                        date_triaged=getattr(lp_task, "date_triaged", None),
                        date_in_progress=getattr(lp_task, "date_in_progress", None),
                        date_fix_committed=getattr(lp_task, "date_fix_committed", None),
                        date_fix_released=getattr(lp_task, "date_fix_released", None),
                        milestone=getattr(lp_task_milestone, "name", None),
                    )
                )

            return new_tasks
        except TimeoutError as exc:
            raise self._wrap_timeout(exc) from exc

    def get_bug_task_by_url(self, task_url: str) -> BugTaskRecord | None:
        """Fetch a Launchpad bug task by URL."""
        lp = self._get_lp_object()

        try:
            try:
                lp_task = lp.load(task_url)
            except NotFound:
                return None

            assignee = None
            if hasattr(lp_task, "assignee"):
                assignee_data = lp_task.assignee
                if hasattr(assignee_data, "name") and hasattr(assignee_data, "display_name"):
                    assignee = UserRecord(
                        username=assignee_data.name,
                        display_name=assignee_data.display_name,
                        profile_url=f"{LP_BASE_USER_URL}{assignee_data.name}",
                    )

            target = None
            package_name = None
            if hasattr(lp_task, "target"):
                target = str(lp_task.target)
                split_target = target.split("/")
                if len(split_target) > 0:
                    package_name = split_target[-1]

            lp_task_milestone = getattr(lp_task, "milestone", None)
            return BugTaskRecord(
                title=getattr(lp_task, "title", ""),
                target=target,
                package_name=package_name,
                importance=getattr(lp_task, "importance", None),
                status=getattr(lp_task, "status", None),
                date_assigned=getattr(lp_task, "date_assigned", None),
                date_closed=getattr(lp_task, "date_closed", None),
                date_created=getattr(lp_task, "date_created", None),
                date_left_closed=getattr(lp_task, "date_left_closed", None),
                date_left_new=getattr(lp_task, "date_left_new", None),
                date_incomplete=getattr(lp_task, "date_incomplete", None),
                date_confirmed=getattr(lp_task, "date_confirmed", None),
                date_triaged=getattr(lp_task, "date_triaged", None),
                date_in_progress=getattr(lp_task, "date_in_progress", None),
                date_fix_committed=getattr(lp_task, "date_fix_committed", None),
                date_fix_released=getattr(lp_task, "date_fix_released", None),
                milestone=getattr(lp_task_milestone, "name", None),
                assignee=assignee,
            )
        except TimeoutError as exc:
            raise self._wrap_timeout(exc) from exc

    def get_bug_metadata(self, bug_id: str) -> BugRecord | None:
        """Fetch a Launchpad bug without comments or tasks."""
        lp_bug = self._fetch_lp_bug_by_id(bug_id)
        if lp_bug is None:
            return None

        try:
            return BugRecord(
                provider_name=self.provider_name,
                id=str(getattr(lp_bug, "id", "")),
                title=getattr(lp_bug, "title", ""),
                description=getattr(lp_bug, "description", None),
                created_at=getattr(lp_bug, "date_created", None),
                updated_at=getattr(lp_bug, "date_last_updated", None),
                last_message_at=getattr(lp_bug, "date_last_message", None),
                last_patch_at=getattr(lp_bug, "latest_patch_uploaded", None),
                tags=getattr(lp_bug, "tags", []),
            )
        except TimeoutError as exc:
            raise self._wrap_timeout(exc) from exc

    def search_bugs(self, query: BugSearchRecord) -> list[BugRecord]:
        """Search Launchpad bugs using BugSearchRecord criteria."""
        if query.status is not None and query.status not in VALID_BUG_STATUSES:
            raise ValueError(f"Invalid bug status provided: '{query.status}'.")

        if query.importance is not None and query.importance not in VALID_BUG_IMPORTANCES:
            raise ValueError(f"Invalid bug importance provided: '{query.importance}'.")

        search_params: dict[str, Any] = {}

        if query.title is not None:
            search_params["search_text"] = query.title

        if query.tags:
            search_params["tags"] = query.tags
            search_params["tags_combinator"] = "All"

        if query.created_before is not None:
            search_params["created_before"] = query.created_before

        if query.created_since is not None:
            search_params["created_since"] = query.created_since

        if query.modified_since is not None:
            search_params["modified_since"] = query.modified_since

        try:
            if query.owner is not None:
                search_params["owner"] = self._get_lp_object().people[query.owner.username]

            if query.assignee is not None:
                search_params["assignee"] = self._get_lp_object().people[query.assignee.username]

            if query.milestone is not None:
                search_params["milestone"] = self._get_distro_object("ubuntu").getMilestone(
                    name=query.milestone
                )

            if query.status is not None:
                search_params["status"] = query.status

            if query.importance is not None:
                search_params["importance"] = query.importance

            task_results = self._get_lp_object().bugs.searchTasks(**search_params)

            bugs: list[BugRecord] = []
            seen_bug_ids: set[str] = set()

            for lp_task in task_results:
                if not hasattr(lp_task, "bug") or lp_task.bug is None:
                    continue

                lp_bug = lp_task.bug
                bug_id = str(getattr(lp_bug, "id", ""))
                if bug_id in seen_bug_ids:
                    continue
                seen_bug_ids.add(bug_id)

                bugs.append(
                    BugRecord(
                        provider_name=self.provider_name,
                        id=bug_id,
                        title=getattr(lp_bug, "title", ""),
                        description=getattr(lp_bug, "description", None),
                        created_at=getattr(lp_bug, "date_created", None),
                        updated_at=getattr(lp_bug, "date_last_updated", None),
                        last_message_at=getattr(lp_bug, "date_last_message", None),
                        last_patch_at=getattr(lp_bug, "latest_patch_uploaded", None),
                        tags=getattr(lp_bug, "tags", []),
                    )
                )

            return bugs
        except TimeoutError as exc:
            raise self._wrap_timeout(exc) from exc

    def get_bug(self, bug_id: str) -> BugRecord | None:
        """Fetch a Launchpad bug by identifier."""
        lp_bug = self._fetch_lp_bug_by_id(bug_id)
        if lp_bug is None:
            return None

        try:
            tasks: list[BugTaskRecord] = []
            if hasattr(lp_bug, "bug_tasks"):
                for task in lp_bug.bug_tasks:
                    task_record = self.get_bug_task_by_url(str(task))
                    if task_record is not None:
                        tasks.append(task_record)

            comments: list[CommentRecord] = []
            if hasattr(lp_bug, "messages"):
                for msg in lp_bug.messages:
                    if not getattr(msg, "visible", True):
                        continue
                    author = None
                    if hasattr(msg, "owner") and msg.owner is not None:
                        owner_data = msg.owner
                        owner_name = getattr(owner_data, "name", None)
                        author = UserRecord(
                            username=owner_name,
                            display_name=getattr(owner_data, "display_name", None),
                            profile_url=f"{LP_BASE_USER_URL}{owner_name}" if owner_name else None,
                        )

                    comments.append(
                        CommentRecord(
                            author=author,
                            content=getattr(msg, "content", ""),
                            created_at=getattr(msg, "date_created", None),
                            edited_at=getattr(msg, "date_last_edited", None),
                        )
                    )

            return BugRecord(
                provider_name=self.provider_name,
                id=str(getattr(lp_bug, "id", "")),
                title=getattr(lp_bug, "title", ""),
                description=getattr(lp_bug, "description", None),
                created_at=getattr(lp_bug, "date_created", None),
                updated_at=getattr(lp_bug, "date_last_updated", None),
                last_message_at=getattr(lp_bug, "date_last_message", None),
                last_patch_at=getattr(lp_bug, "latest_patch_uploaded", None),
                tags=getattr(lp_bug, "tags", []),
                bug_tasks=tasks,
                comments=comments,
            )
        except TimeoutError as exc:
            raise self._wrap_timeout(exc) from exc

    def submit_bug(self, submission: BugSubmissionRecord) -> BugRecord | None:
        """Submit a new bug to Launchpad and return the created record."""
        self._validate_bug_submission(submission)

        try:
            first_package = self._get_lp_source_package_object(
                submission.package_names[0], "ubuntu"
            )
            if first_package is None:
                raise ValueError(
                    f"Package '{submission.package_names[0]}' not found in Launchpad."
                )

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
                created_lp_bug.subscribe(person=self._get_lp_object().people[subscriber.username])

            return BugRecord(
                provider_name=self.provider_name,
                id=str(getattr(created_lp_bug, "id", "")),
                title=getattr(created_lp_bug, "title", ""),
                description=getattr(created_lp_bug, "description", None),
                created_at=getattr(created_lp_bug, "date_created", None),
                updated_at=getattr(created_lp_bug, "date_last_updated", None),
                last_message_at=getattr(created_lp_bug, "date_last_message", None),
                last_patch_at=getattr(created_lp_bug, "latest_patch_uploaded", None),
                tags=getattr(created_lp_bug, "tags", []),
                bug_tasks=tasks if tasks is not None else [],
            )
        except TimeoutError as exc:
            raise self._wrap_timeout(exc) from exc
