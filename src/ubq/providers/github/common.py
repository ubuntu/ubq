"""Shared helpers for GitHub data providers."""

from datetime import datetime, timezone
from typing import Any

from ubq.models import UserRecord
from ubq.providers.github.provider import GH_BASE_URL

_GH_API_REPO_PREFIX = "https://api.github.com/repos/"


def parse_dt(s: str | None) -> datetime | None:
    """Parse a GitHub ISO-8601 datetime string into a timezone-aware datetime."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_github_id(raw_id: str, label: str = "ID") -> tuple[str, str, int]:
    """Parse 'owner/repo#number' into (owner, repo, number).

    ``label`` is used in the error message to describe the kind of identifier
    (e.g. "bug ID", "merge request ID").
    """
    try:
        repo_part, num_str = raw_id.rsplit("#", 1)
        owner, name = repo_part.split("/", 1)
        return owner, name, int(num_str)
    except (ValueError, AttributeError) as exc:
        raise ValueError(
            f"Invalid {label} format '{raw_id}'. Expected 'owner/repo#number'."
        ) from exc


def user_record(node: dict[str, Any] | None) -> UserRecord | None:
    """Build a ``UserRecord`` from a GitHub GraphQL or REST user node."""
    if not node:
        return None
    login = node.get("login")
    if not login:
        return None
    return UserRecord(
        username=login,
        display_name=node.get("name") or login,
        profile_url=f"{GH_BASE_URL}/{login}",
    )


def parse_repo_from_api_url(repo_url: str) -> tuple[str, str] | None:
    """Extract ``(owner, repo)`` from a GitHub API repository URL.

    Returns ``None`` if *repo_url* doesn't match the expected format.
    """
    if not repo_url.startswith(_GH_API_REPO_PREFIX):
        return None
    repo_path = repo_url[len(_GH_API_REPO_PREFIX) :]
    owner, _, repo = repo_path.partition("/")
    if not owner or not repo:
        return None
    return owner, repo
