"""GitHub merge request (pull request) data provider."""

from typing import Any

from ubq.models import MergeRequestRecord, UserRecord
from ubq.providers.github.common import (
    parse_dt,
    parse_repo_from_api_url,
    user_record,
)
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
        author=user_record(node.get("author")),
        assignees=[r for n in assignee_nodes if (r := user_record(n)) is not None],
        created_at=parse_dt(node.get("createdAt")),
        updated_at=parse_dt(node.get("updatedAt")),
        merged_at=parse_dt(node.get("mergedAt")),
    )


class GitHubMergeRequestProvider(GitHubProvider, MergeRequestProvider):
    """Provider implementation for GitHub pull requests as merge requests."""

    def get_merge_request(
        self,
        author: str,
        project: str,
        branch: str,
        merge_request_id: str,
    ) -> MergeRequestRecord | None:
        """Fetch a GitHub pull request by owner, repo, and pull request number.

        The ``branch`` argument is accepted for interface compatibility but is
        not required to identify a GitHub pull request.
        """
        try:
            number = int(merge_request_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid merge request ID '{merge_request_id}'. Expected an integer."
            ) from exc
        data = self._graphql(
            _PR_QUERY, {"owner": author, "name": project, "number": number}
        )
        node = (data.get("repository") or {}).get("pullRequest")
        if node is None:
            return None
        return _pr_node_to_record(self.provider_name, author, project, node)

    def get_merge_requests_from_user(self, user_id: str) -> list[MergeRequestRecord]:
        """Fetch open pull requests authored by the given GitHub username."""
        response = self._rest_get(
            "/search/issues",
            {"q": f"type:pr author:{user_id}", "per_page": 100},
        )

        results: list[MergeRequestRecord] = []
        for item in response.get("items") or []:
            repo_url = item.get("repository_url", "")
            parsed = parse_repo_from_api_url(repo_url)
            if parsed is None:
                continue
            owner_part, repo_part = parsed
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
                    created_at=parse_dt(item.get("created_at")),
                    updated_at=parse_dt(item.get("updated_at")),
                    merged_at=parse_dt((item.get("pull_request") or {}).get("merged_at")),
                )
            )
        return results
