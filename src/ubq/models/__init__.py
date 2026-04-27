"""Generic Ubuntu data models."""

from ubq.models.common import CommentRecord, UserRecord
from ubq.models.bug import BugRecord, BugTaskRecord

__all__ = [
    "CommentRecord",
    "UserRecord",
    "BugRecord",
    "BugTaskRecord",
]
