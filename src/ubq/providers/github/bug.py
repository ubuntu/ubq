"""GitHub bug (issue) data provider."""

from datetime import datetime, timezone
from typing import Any

from ubq.models import (
    BugRecord,
    BugSearchRecord,
    BugSubmissionRecord,
    BugTaskRecord,
    CommentRecord,
    UserRecord,
)
from ubq.providers.bug import BugProvider
from ubq.providers.github.provider import GH_BASE_URL, GitHubProvider

_ISSUE_QUERY = """
query GetIssue($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      number title body url state createdAt updatedAt closedAt lastEditedAt
      labels(first: 20) { nodes { name } }
      author { login }
      assignees(first: 5) { nodes { login name } }
      comments(first: 100) {
        nodes {
          body createdAt lastEditedAt
          author { login }
        }
      }
    }
  }
}
"""

_ISSUE_METADATA_QUERY = """
query GetIssueMetadata($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      number title body url state createdAt updatedAt closedAt lastEditedAt
      labels(first: 20) { nodes { name } }
      author { login }
      assignees(first: 5) { nodes { login name } }
    }
  }
}
"""


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_bug_id(bug_id: str) -> tuple[str, str, int]:
    """Parse 'owner/repo#number' into (owner, repo, number)."""
    try:
        repo_part, num_str = bug_id.rsplit("#", 1)
        owner, name = repo_part.split("/", 1)
        return owner, name, int(num_str)
    except (ValueError, AttributeError) as exc:
        raise ValueError(
            f"Invalid bug ID format '{bug_id}'. Expected 'owner/repo#number'."
        ) from exc


def _user_record(node: dict[str, Any] | None) -> UserRecord | None:
    if not node:
        return None
    login = node.get("login")
    if not login:
        return None
    return UserRecord(
        username=login,
        display_name=node.get("name") or login,
        profile_url=f"https://github.com/{login}",
    )


def _issue_to_bug_record(
    provider_name: str,
    owner: str,
    repo: str,
    node: dict[str, Any],
    with_comments: bool = True,
) -> BugRecord:
    bug_id = f"{owner}/{repo}#{node['number']}"
    assignee_nodes = node.get("assignees", {}).get("nodes") or []
    assignee = _user_record(assignee_nodes[0]) if assignee_nodes else None

    comments: list[CommentRecord] = []
    if with_comments:
        for c in node.get("comments", {}).get("nodes") or []:
            comments.append(
                CommentRecord(
                    author=_user_record(c.get("author")),
                    content=c.get("body") or "",
                    created_at=_parse_dt(c.get("createdAt")),
                    edited_at=_parse_dt(c.get("lastEditedAt")),
                )
            )

    return BugRecord(
        provider_name=provider_name,
        id=bug_id,
        title=node["title"],
        description=node.get("body"),
        tags=[lbl["name"] for lbl in (node.get("labels", {}).get("nodes") or [])],
        comments=comments,
        created_at=_parse_dt(node.get("createdAt")),
        updated_at=_parse_dt(node.get("updatedAt")),
        owner=_user_record(node.get("author")),
        assignee=assignee,
    )


class GitHubBugProvider(GitHubProvider, BugProvider):
    """Provider implementation for GitHub issues as bugs."""

    def get_bug_metadata(self, bug_id: str) -> BugRecord | None:
        """Fetch a single GitHub issue without comments."""
        owner, repo, number = _parse_bug_id(bug_id)
        data = self._graphql(
            _ISSUE_METADATA_QUERY, {"owner": owner, "name": repo, "number": number}
        )
        node = (data.get("repository") or {}).get("issue")
        if node is None:
            return None
        return _issue_to_bug_record(self.provider_name, owner, repo, node, with_comments=False)

    def get_bug(self, bug_id: str) -> BugRecord | None:
        """Fetch a single GitHub issue with comments."""
        owner, repo, number = _parse_bug_id(bug_id)
        data = self._graphql(_ISSUE_QUERY, {"owner": owner, "name": repo, "number": number})
        node = (data.get("repository") or {}).get("issue")
        if node is None:
            return None
        return _issue_to_bug_record(self.provider_name, owner, repo, node, with_comments=True)

    def search_bugs(self, query: BugSearchRecord) -> list[BugRecord]:
        """Search GitHub issues using BugSearchRecord criteria."""
        q_parts: list[str] = ["is:issue"]

        if query.title is not None:
            q_parts.append(query.title)
        for tag in query.tags:
            q_parts.append(f"label:{tag}")
        if query.status is not None:
            q_parts.append(f"is:{query.status}")
        if query.assignee is not None and query.assignee.username:
            q_parts.append(f"assignee:{query.assignee.username}")
        if query.owner is not None and query.owner.username:
            q_parts.append(f"author:{query.owner.username}")
        if query.created_since is not None:
            since_str = query.created_since.strftime("%Y-%m-%d")
            q_parts.append(f"created:>={since_str}")
        if query.created_before is not None:
            before_str = query.created_before.strftime("%Y-%m-%d")
            q_parts.append(f"created:<={before_str}")
        if query.modified_since is not None:
            mod_str = query.modified_since.strftime("%Y-%m-%d")
            q_parts.append(f"updated:>={mod_str}")

        response = self._rest_get(
            "/search/issues",
            {"q": " ".join(q_parts), "per_page": 100},
        )

        results: list[BugRecord] = []
        for item in response.get("items") or []:
            repo_url = item.get("repository_url", "")
            repo_path = repo_url.removeprefix("https://api.github.com/repos/")
            owner_part, _, repo_part = repo_path.partition("/")
            number = item["number"]
            assignee_data = item.get("assignee")
            assignee = (
                UserRecord(
                    username=assignee_data["login"],
                    display_name=assignee_data.get("login"),
                    profile_url=f"{GH_BASE_URL}/{assignee_data['login']}",
                )
                if assignee_data
                else None
            )
            user_data = item.get("user")
            owner_record = (
                UserRecord(
                    username=user_data["login"],
                    display_name=user_data.get("login"),
                    profile_url=f"{GH_BASE_URL}/{user_data['login']}",
                )
                if user_data
                else None
            )
            results.append(
                BugRecord(
                    provider_name=self.provider_name,
                    id=f"{owner_part}/{repo_part}#{number}",
                    title=item["title"],
                    description=item.get("body"),
                    tags=[lbl["name"] for lbl in (item.get("labels") or [])],
                    created_at=_parse_dt(item.get("created_at")),
                    updated_at=_parse_dt(item.get("updated_at")),
                    owner=owner_record,
                    assignee=assignee,
                )
            )
        return results

    def submit_bug(self, submission: BugSubmissionRecord) -> BugRecord | None:
        """Create a new GitHub issue and return the created record.

        The first entry in package_names is used as the target repository in
        'owner/repo' format.
        """
        if not submission.package_names:
            raise ValueError(
                "At least one repository must be provided in package_names "
                "as 'owner/repo' for GitHub bug submission."
            )

        target_repo = submission.package_names[0]
        try:
            owner, repo = target_repo.split("/", 1)
        except ValueError as exc:
            raise ValueError(
                f"package_names[0] must be 'owner/repo', got '{target_repo}'."
            ) from exc

        body: dict[str, Any] = {"title": submission.title}
        if submission.description is not None:
            body["body"] = submission.description
        if submission.tags:
            body["labels"] = submission.tags
        if submission.assignee is not None and submission.assignee.username:
            body["assignees"] = [submission.assignee.username]

        item = self._rest_post(f"/repos/{owner}/{repo}/issues", body)

        number = item["number"]
        bug_id = f"{owner}/{repo}#{number}"
        user_data = item.get("user")
        owner_record = (
            UserRecord(
                username=user_data["login"],
                display_name=user_data.get("login"),
                profile_url=f"{GH_BASE_URL}/{user_data['login']}",
            )
            if user_data
            else None
        )
        assignee_data = item.get("assignee")
        assignee = (
            UserRecord(
                username=assignee_data["login"],
                display_name=assignee_data.get("login"),
                profile_url=f"{GH_BASE_URL}/{assignee_data['login']}",
            )
            if assignee_data
            else None
        )

        return BugRecord(
            provider_name=self.provider_name,
            id=bug_id,
            title=item["title"],
            description=item.get("body"),
            tags=[lbl["name"] for lbl in (item.get("labels") or [])],
            created_at=_parse_dt(item.get("created_at")),
            updated_at=_parse_dt(item.get("updated_at")),
            owner=owner_record,
            assignee=assignee,
            bug_tasks=[
                BugTaskRecord(
                    title=item["title"],
                    target=f"{GH_BASE_URL}/{owner}/{repo}",
                    status=item.get("state"),
                )
            ],
        )
