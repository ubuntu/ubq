"""GitHub merge request (pull request) data provider."""

from datetime import datetime
from typing import Any

from ubq.models import MergeRequestRecord, MergeRequestVoteRecord, UserRecord
from ubq.providers.github.common import (
    parse_dt,
    parse_repo_from_api_url,
    user_record,
)
from ubq.providers.github.provider import GH_BASE_URL, GitHubProvider
from ubq.providers.merge_request import MergeRequestProvider

STATE_TO_VOTE_VALUE = {
    "APPROVED": 1,  # Approve/Like
    "CHANGES_REQUESTED": -1,  # Disapprove/Dislike
    "COMMENTED": 0,  # Neutral comment
    "PENDING": 0,  # Neutral - review pending
}

STATE_TO_VOTE_LABEL = {
    "APPROVED": "APPROVE",
    "CHANGES_REQUESTED": "DISAPPROVE",
    "COMMENTED": "COMMENT",
    "PENDING": "PENDING",
}

_PR_QUERY = """
query GetPullRequest($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      number title body url state
      createdAt updatedAt closedAt mergedAt
      headRefName baseRefName
      author { login }
      assignees(first: 5) { nodes { login name } }
      reviews(first: 100) {
        nodes {
          author { login url }
          state
          submittedAt
          body
          commit { oid }
        }
      }
    }
  }
}
"""


def _process_reviews_to_votes(reviews: list) -> list[MergeRequestVoteRecord]:
    """
    Convert GitHub review nodes to MergeRequestVoteRecord objects.
    """
    votes = []
    for review in reviews:
        author = review.get("author")
        if not author:
            continue

        state = review.get("state", "")
        voter = UserRecord(
            username=author.get("login", ""),
            display_name=author.get("login", ""),  # GitHub uses same value
            profile_url=author.get("url", ""),
        )

        vote = MergeRequestVoteRecord(
            voter=voter,
            vote_value=STATE_TO_VOTE_VALUE.get(state, 0),
            vote=STATE_TO_VOTE_LABEL.get(state, state),
            message=review.get("body") or "",
            voted_at=_parse_datetime(review.get("submittedAt")),
            unvoted_at=None,  # GitHub doesn't track when reviews are dismissed
        )
        votes.append(vote)

    return votes


def _parse_datetime(dt_str: str | None) -> datetime | None:
    """Parse ISO 8601 datetime string from GitHub."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _pr_node_to_record(
    provider_name: str, owner: str, repo: str, node: dict[str, Any]
) -> MergeRequestRecord:
    number = node["number"]
    mr_id = f"{owner}/{repo}#{number}"
    review_nodes = node.get("reviews", {}).get("nodes") or []

    # Process reviews into votes
    votes = _process_reviews_to_votes(review_nodes)

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
        assignees=[vote.voter for vote in votes],  # Use voters as assignees
        created_at=parse_dt(node.get("createdAt")),
        updated_at=parse_dt(node.get("updatedAt")),
        merged_at=parse_dt(node.get("mergedAt")),
        votes=votes,
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
        data = self._graphql(_PR_QUERY, {"owner": author, "name": project, "number": number})
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
                    votes=[],  # Search API doesn't include reviews
                )
            )
        return results
