"""Generic Ubuntu data models."""

from ubq.models.bug import BugRecord, BugTaskRecord
from ubq.models.common import CommentRecord, UserRecord
from ubq.models.merge_request import MergeRequestRecord
from ubq.models.package import PackageRecord
from ubq.models.version import VersionRecord

__all__ = [
    "CommentRecord",
    "UserRecord",
    "BugRecord",
    "BugTaskRecord",
    "VersionRecord",
    "PackageRecord",
    "MergeRequestRecord",
]
