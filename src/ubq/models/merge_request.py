"""Merge request model records."""

from dataclasses import dataclass
from datetime import datetime

from ubq.models.common import UserRecord
from ubq.models.package import PackageRecord


@dataclass(frozen=True, slots=True)
class MergeRequestRecord:
    """Merge request or pull request metadata."""

    provider_name: str
    id: str
    title: str
    description: str
    status: str | None = None
    source_branch: str | None = None
    target_branch: str | None = None
    web_url: str | None = None
    author: UserRecord | None = None
    assignee: UserRecord | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    merged_at: datetime | None = None
    package: PackageRecord | None = None
