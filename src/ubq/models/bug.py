"""Bug model records."""

from dataclasses import dataclass, field
from datetime import datetime

from ubq.models.common import CommentRecord, UserRecord
from ubq.models.package import PackageRecord


@dataclass(frozen=True, slots=True)
class BugTaskRecord:
    """Subtask record for a bug."""

    title: str
    target: str | None = None
    importance: str | None = None
    status: str | None = None
    date_assigned: datetime | None = None
    date_closed: datetime | None = None
    date_created: datetime | None = None
    date_left_closed: datetime | None = None
    date_left_new: datetime | None = None
    date_incomplete: datetime | None = None
    date_confirmed: datetime | None = None
    date_triaged: datetime | None = None
    date_in_progress: datetime | None = None
    date_fix_committed: datetime | None = None
    date_fix_released: datetime | None = None
    milestone: str | None = None
    owner: UserRecord | None = None
    assignee: UserRecord | None = None


@dataclass(frozen=True, slots=True)
class BugRecord:
    """General bug information record."""

    provider_name: str
    id: str
    title: str
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    comments: list[CommentRecord] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_message_at: datetime | None = None
    last_patch_at: datetime | None = None
    owner: UserRecord | None = None
    assignee: UserRecord | None = None
    bug_tasks: list[BugTaskRecord] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BugSubmissionRecord:
    """General bug submission information record."""

    provider_name: str
    title: str
    packages: list[PackageRecord] = field(default_factory=list)
    description: str | None = None
    importance: str | None = None
    status: str | None = None
    tags: list[str] = field(default_factory=list)
    subscribers: list[UserRecord] = field(default_factory=list)
    assignee: UserRecord | None = None
    private: bool = False
    milestone: str | None = None
