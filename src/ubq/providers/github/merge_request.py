"""GitHub merge request (pull request) data provider."""

from datetime import datetime, timezone
from typing import Any

from ubq.models import MergeRequestRecord, UserRecord
from ubq.providers.github.provider import GH_BASE_URL, GitHubProvider
from ubq.providers.merge_request import MergeRequestProvider

_PR_QUERY = """
query GetPullRequest($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      number title body url state
      createdAt updatedAt closedAt mergedAt
      headRefName baseRefName
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


def _parse_mr_id(mr_id: str) -> tuple[str, str, int]:
    """Parse 'owner/repo#number' into (owner, repo, number)."""
    try:
        repo_part, num_str = mr_id.rsplit("#", 1)
        owner, name = repo_part.split("/", 1)
        return owner, name, int(num_str)
    except (ValueError, AttributeError) as exc:
        raise ValueError(
            f"Invalid merge request ID format '{mr_id}'. Expected 'owner/repo#number'."
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
        profile_url=f"{GH_BASE_URL}/{login}",
    )


def _pr_node_to_record(
    provider_name: str, owner: str, repo: str, node: dict[str, Any]
) -> MergeRequestRecord:
    number = node["number"]
    mr_id = f"{owner}/{repo}#{number}"
    assignee_nodes = node.get("assignees", {}).get("nodes") or []
    return MergeRequestRecord(
        provider_name=provider_name,
        id=mr_id,
        title=node["title"],
        description=node.get("body") or "",
        status=node.get("state", "").lower() or None,
        source_branch=node.get("headRefName"),
        target_branch=node.get("baseRefName"),
        web_url=node.get("url"),
        author=_user_record(node.get("author")),
        assignees=[r for n in assignee_nodes if (r := _user_record(n)) is not None],
        created_at=_parse_dt(node.get("createdAt")),
        updated_at=_parse_dt(node.get("updatedAt")),
        merged_at=_parse_dt(node.get("mergedAt")),
    )


class GitHubMergeRequestProvider(GitHubProvider, MergeRequestProvider):
    """Provider implementation for GitHub pull requests as merge requests."""

    def get_merge_request(self, merge_request_id: str) -> MergeRequestRecord | None:
        """Fetch a GitHub pull request by 'owner/repo#number' identifier."""
        owner, repo, number = _parse_mr_id(merge_request_id)
        data = self._graphql(_PR_QUERY, {"owner": owner, "name": repo, "number": number})
        node = (data.get("repository") or {}).get("pullRequest")
        if node is None:
            return None
        return _pr_node_to_record(self.provider_name, owner, repo, node)

    def get_merge_requests_from_user(self, user_id: str) -> list[MergeRequestRecord]:
        """Fetch open pull requests authored by the given GitHub username."""
        response = self._rest_get(
            "/search/issues",
            {"q": f"type:pr author:{user_id}", "per_page": 100},
        )

        results: list[MergeRequestRecord] = []
        for item in response.get("items") or []:
            repo_url = item.get("repository_url", "")
            repo_path = repo_url.removeprefix("https://api.github.com/repos/")
            owner_part, _, repo_part = repo_path.partition("/")
            number = item["number"]
            mr_id = f"{owner_part}/{repo_part}#{number}"

            user_data = item.get("user")
            author = (
                UserRecord(
                    username=user_data["login"],
                    display_name=user_data.get("login"),
                    profile_url=f"{GH_BASE_URL}/{user_data['login']}",
                )
                if user_data
                else None
            )
            assignee_data = item.get("assignee")
            assignees = (
                [
                    UserRecord(
                        username=assignee_data["login"],
                        display_name=assignee_data.get("login"),
                        profile_url=f"{GH_BASE_URL}/{assignee_data['login']}",
                    )
                ]
                if assignee_data
                else []
            )
            pull_request_url = item.get("pull_request", {}).get("url") or item.get("html_url")

            results.append(
                MergeRequestRecord(
                    provider_name=self.provider_name,
                    id=mr_id,
                    title=item["title"],
                    description=item.get("body") or "",
                    status=item.get("state"),
                    web_url=pull_request_url,
                    author=author,
                    assignees=assignees,
                    created_at=_parse_dt(item.get("created_at")),
                    updated_at=_parse_dt(item.get("updated_at")),
                    merged_at=_parse_dt((item.get("pull_request") or {}).get("merged_at")),
                )
            )
        return results
