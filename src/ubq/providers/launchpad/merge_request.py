"""Common interface for merge request data providers."""

from ubq.models import MergeRequestRecord, MergeRequestVoteRecord, UserRecord
from ubq.providers.launchpad.provider import LP_BASE_USER_URL, LaunchpadProvider
from ubq.providers.merge_request import MergeRequestProvider


class LaunchpadMergeRequestProvider(LaunchpadProvider, MergeRequestProvider):
    """Contract that all merge request providers must implement."""

    def get_merge_request(self, merge_request_id: str) -> MergeRequestRecord | None:
        """Fetch a merge request by provider-specific identifier."""
        return None

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
                votes = []
                if hasattr(mr, "votes_collection"):
                    for vote in mr.votes_collection:
                        if hasattr(vote, "reviewer"):
                            reviewer_data = vote.reviewer
                            reviewer_name = getattr(reviewer_data, "name", None)
                            if reviewer_name is None:
                                continue

                            user_record = UserRecord(
                                username=reviewer_name,
                                display_name=getattr(reviewer_data, "display_name", None),
                                profile_url=f"{LP_BASE_USER_URL}{reviewer_name}",
                            )

                            vote_type = getattr(vote, "vote", None)

                            # Set vote value based on standard vote strings
                            vote_value = 0

                            if vote_type == "Approve":
                                vote_value = 1
                            elif vote_type == "Needs Fixing" or vote_type == "Disapprove" or vote_type == "Needs Resubmitting":
                                vote_value = -1

                            message = None
                            comment = getattr(vote, "comment", None)
                            if comment:
                                message = getattr(comment, "content", None)

                            vote_record = MergeRequestVoteRecord(
                                voter=user_record,
                                vote_value=vote_value,
                                vote=vote_type,
                                message=message,
                                voted_at=getattr(vote, "date_created", None),
                                unvoted_at=getattr(vote, "date_deleted", None),
                            )
                            votes.append(vote_record)

                mr_id = ""
                if hasattr(mr, "web_link"):
                    mr_id = mr.web_link.rsplit("/", 1)[-1]

                added_lines = None
                removed_lines = None

                if hasattr(mr, "preview_diff"):
                    diff_data = mr.preview_diff
                    diff_added = getattr(diff_data, "added_lines_count", None)
                    diff_removed = getattr(diff_data, "removed_lines_count", None)
                    added_lines = int(diff_added) if diff_added is not None else None
                    removed_lines = int(diff_removed) if diff_removed is not None else None

                converted_merge_requests.append(
                    MergeRequestRecord(
                        provider_name=self.provider_name,
                        id=mr_id,
                        title="",
                        description=getattr(mr, "description", "") or "",
                        status=getattr(mr, "queue_status", None),
                        source_branch=getattr(mr, "source_git_path", None),
                        target_branch=getattr(mr, "target_git_path", None),
                        web_url=getattr(mr, "web_link", None),
                        assignees=[v.voter for v in votes],
                        created_at=getattr(mr, "date_created", None),
                        merged_at=getattr(mr, "date_merged", None),
                        added_lines=added_lines,
                        removed_lines=removed_lines,
                        votes=votes,
                    )
                )
            except TimeoutError as exc:
                raise self._wrap_timeout(exc) from exc

        return converted_merge_requests
