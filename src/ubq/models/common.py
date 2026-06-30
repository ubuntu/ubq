"""Shared model records."""

from dataclasses import dataclass
from datetime import datetime
from os import PathLike
from pathlib import Path


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

    @classmethod
    def from_file(
        cls,
        path: str | PathLike[str],
        *,
        username: str | None = None,
    ) -> "ProviderCredentials":
        """Build credentials by reading a token from a file.

        The file's entire contents are read and stripped of surrounding
        whitespace (trailing newlines are common in OAuth credential files).
        Raises ``FileNotFoundError`` if the file does not exist and
        ``ValueError`` if it is empty after stripping.
        """
        token = Path(path).read_text(encoding="utf-8").strip()
        if not token:
            raise ValueError(f"Credentials file is empty: {path}")

        return cls(username=username, token=token)


@dataclass(frozen=True, slots=True)
class AuthContext:
    """Authentication context used when creating a provider session."""

    provider_name: str
    credentials: ProviderCredentials | None = None
