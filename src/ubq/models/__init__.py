"""Generic Ubuntu data models."""

from ubq.models.bug import BugRecord, BugTaskRecord
from ubq.models.common import CommentRecord, UserRecord

__all__ = [
    "CommentRecord",
    "UserRecord",
    "BugRecord",
    "BugTaskRecord",
]
