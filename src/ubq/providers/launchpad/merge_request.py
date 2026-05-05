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
        user = self._get_lp_object().people[user_id]
        merge_requests = user.getMergeProposals()

        if merge_requests is None:
            return []

        converted_merge_requests = []
        for mr in merge_requests:
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
                )
            )

        return converted_merge_requests
