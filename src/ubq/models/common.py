"""Shared model records."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class UserRecord:
    """Generic user information."""

    username: str | None = None
    display_name: str | None = None
    profile_url: str | None = None


@dataclass(frozen=True, slots=True)
class CommentRecord:
    """Comment data for a record."""

    author: UserRecord | None = None
    content: str = ""
    created_at: datetime | None = None
    edited_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ProviderCredentials:
    """Credentials used to authenticate with a provider."""

    username: str | None = None
    token: str | None = None


@dataclass(frozen=True, slots=True)
class AuthContext:
    """Authentication context used when creating a provider session."""

    provider_name: str
    credentials: ProviderCredentials | None = None
