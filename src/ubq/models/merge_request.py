"""Merge request model records."""

from dataclasses import dataclass, field
from datetime import datetime

from ubq.models.common import UserRecord
from ubq.models.package import PackageRecord


@dataclass(frozen=True, slots=True)
class MergeRequestVoteRecord:
    """Merge request or pull request vote metadata."""
    voter: UserRecord
    vote_value: int
    vote: str | None = None
    message: str | None = None
    voted_at: datetime | None = None
    unvoted_at: datetime | None = None

@dataclass(frozen=True, slots=True)
class MergeRequestRecord:
    """Merge request or pull request metadata."""

    provider_name: str
    id: str
    title: str
    description: str | None = None
    status: str | None = None
    source_branch: str | None = None
    target_branch: str | None = None
    web_url: str | None = None
    author: UserRecord | None = None
    assignees: list[UserRecord] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    merged_at: datetime | None = None
    package: PackageRecord | None = None
    added_lines: int | None = None
    removed_lines: int | None = None
    votes: list[MergeRequestVoteRecord] = field(default_factory=list)
