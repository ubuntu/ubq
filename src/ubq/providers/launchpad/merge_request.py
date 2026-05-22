"""Common interface for merge request data providers."""

from ubq.models import MergeRequestRecord, UserRecord
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
                assignees = []
                if hasattr(mr, "votes_collection"):
                    for vote in mr.votes_collection:
                        if hasattr(vote, "reviewer"):
                            reviewer_data = vote.reviewer
                            assignees.append(
                                UserRecord(
                                    username=reviewer_data.name,
                                    display_name=reviewer_data.display_name,
                                    profile_url=f"{LP_BASE_USER_URL}{reviewer_data.name}",
                                )
                            )

                mr_id = ""
                if hasattr(mr, "web_link"):
                    mr_id = mr.web_link.rsplit("/", 1)[-1]

                added_lines = None
                removed_lines = None

                if hasattr(mr, "preview_diff"):
                    diff_data = mr.preview_diff
                    added_lines = int(diff_data.added_lines_count)
                    removed_lines = int(diff_data.removed_lines_count)

                converted_merge_requests.append(
                    MergeRequestRecord(
                        provider_name=self.provider_name,
                        id=mr_id,
                        title="",
                        description=mr.description,
                        status=mr.queue_status,
                        source_branch=mr.source_git_path,
                        target_branch=mr.target_git_path,
                        web_url=mr.web_link,
                        assignees=assignees,
                        created_at=mr.date_created,
                        merged_at=mr.date_merged,
                        added_lines=added_lines,
                        removed_lines=removed_lines,
                    )
                )
            except TimeoutError as exc:
                raise self._wrap_timeout(exc) from exc

        return converted_merge_requests
