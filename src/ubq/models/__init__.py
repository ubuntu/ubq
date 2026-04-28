"""Generic Ubuntu data models."""

from ubq.models.bug import BugRecord, BugTaskRecord
from ubq.models.common import (
    AuthContext,
    AuthScope,
    CommentRecord,
    ProviderCredentials,
    UserRecord,
)
from ubq.models.merge_request import MergeRequestRecord
from ubq.models.package import PackageRecord
from ubq.models.version import VersionRecord

__all__ = [
    "AuthScope",
    "ProviderCredentials",
    "AuthContext",
    "CommentRecord",
    "UserRecord",
    "BugRecord",
    "BugTaskRecord",
    "VersionRecord",
    "PackageRecord",
    "MergeRequestRecord",
]
