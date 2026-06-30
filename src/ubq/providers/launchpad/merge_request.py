"""Common interface for merge request data providers."""

from typing import Any

from lazr.restfulclient.errors import HTTPError  # type: ignore[import-untyped]

from ubq.models import MergeRequestRecord, MergeRequestVoteRecord, UserRecord
from ubq.providers.launchpad.common import LP_API_BASE_URL
from ubq.providers.launchpad.provider import LP_BASE_USER_URL, LaunchpadProvider
from ubq.providers.merge_request import MergeRequestProvider


class LaunchpadMergeRequestProvider(LaunchpadProvider, MergeRequestProvider):
    """Contract that all merge request providers must implement."""

    def get_merge_request(
        self,
        author: str,
        project: str,
        branch: str,
        merge_request_id: str,
    ) -> MergeRequestRecord | None:
        """Fetch a branch merge proposal by author, project, branch, and id.

        Maps to the Launchpad ``branch_merge_proposal`` resource located at
        ``~<author>/<project>/<branch>/+merge/<id>``.
        """
        lp = self._get_lp_object()
        url = f"{LP_API_BASE_URL}~{author}/{project}/{branch}/+merge/{merge_request_id}"

        try:
            merge_request = lp.load(url)
        except HTTPError as exc:
            if getattr(exc.response, "status", None) == 404:
                return None
            raise
        except TimeoutError as exc:
            raise self._wrap_timeout(exc) from exc

        if merge_request is None:
            return None

        try:
            return self._convert_merge_proposal(merge_request)
        except TimeoutError as exc:
            raise self._wrap_timeout(exc) from exc

    def get_merge_requests_from_user(self, user_id: str) -> list[MergeRequestRecord]:
        """Fetch merge requests assigned to a specific user."""
        try:
            user = self._get_lp_object().people[user_id]
            merge_requests = user.getMergeProposals()
        except TimeoutError as exc:
            raise self._wrap_timeout(exc) from exc

        if merge_requests is None:
            return []

        converted_merge_requests = []
        for mr in merge_requests:
            try:
                converted_merge_requests.append(self._convert_merge_proposal(mr))
            except TimeoutError as exc:
                raise self._wrap_timeout(exc) from exc

        return converted_merge_requests

    def _convert_merge_proposal(self, mr: Any) -> MergeRequestRecord:
        """Convert a Launchpad branch merge proposal into a MergeRequestRecord."""

        # The votes collection contains assigned voters, not vote values :/
        assignees = []
        if hasattr(mr, "votes_collection"):
            for vote in mr.votes_collection:
                if hasattr(vote, "reviewer"):
                    reviewer_data = vote.reviewer
                    reviewer_name = getattr(reviewer_data, "name", None)
                    if reviewer_name is not None:
                        assignees.append(
                            UserRecord(
                                username=reviewer_name,
                                display_name=getattr(reviewer_data, "display_name", None),
                                profile_url=f"{LP_BASE_USER_URL}{reviewer_name}",
                            )
                        )

        # Vote values can be found attached to comments
        votes = []
        if hasattr(mr, "all_comments_collection"):
            for comment in mr.all_comments_collection:
                vote_type = getattr(comment, "vote", None)

                if vote_type is None:
                    continue

                if hasattr(comment, "author"):
                    reviewer_data = comment.author
                    reviewer_name = getattr(reviewer_data, "name", None)
                    if reviewer_name is None:
                        continue

                    user_record = UserRecord(
                        username=reviewer_name,
                        display_name=getattr(reviewer_data, "display_name", None),
                        profile_url=f"{LP_BASE_USER_URL}{reviewer_name}",
                    )

                    # Set vote value based on standard vote strings
                    vote_value = 0

                    if vote_type == "Approve":
                        vote_value = 1
                    elif vote_type in ("Needs Fixing", "Disapprove", "Needs Resubmitting"):
                        vote_value = -1

                    message = None
                    comment_content = getattr(comment, "comment", None)
                    if comment_content:
                        message = getattr(comment_content, "content", None)

                    vote_record = MergeRequestVoteRecord(
                        voter=user_record,
                        vote_value=vote_value,
                        vote=vote_type,
                        message=message,
                        voted_at=getattr(comment, "date_created", None),
                        unvoted_at=getattr(comment, "date_deleted", None),
                    )
                    votes.append(vote_record)

        mr_id = ""
        self_link = getattr(mr, "self_link", None)
        if self_link:
            mr_id = self_link.removeprefix(LP_API_BASE_URL)

        added_lines = None
        removed_lines = None

        if hasattr(mr, "preview_diff"):
            diff_data = mr.preview_diff
            diff_added = getattr(diff_data, "added_lines_count", None)
            diff_removed = getattr(diff_data, "removed_lines_count", None)
            added_lines = int(diff_added) if diff_added is not None else None
            removed_lines = int(diff_removed) if diff_removed is not None else None

        return MergeRequestRecord(
            provider_name=self.provider_name,
            id=mr_id,
            title="",
            description=getattr(mr, "description", "") or "",
            status=getattr(mr, "queue_status", None),
            source_branch=getattr(mr, "source_git_path", None),
            target_branch=getattr(mr, "target_git_path", None),
            web_url=getattr(mr, "web_link", None),
            assignees=assignees,
            created_at=getattr(mr, "date_created", None),
            merged_at=getattr(mr, "date_merged", None),
            added_lines=added_lines,
            removed_lines=removed_lines,
            votes=votes,
        )
