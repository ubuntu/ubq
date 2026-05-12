#!/usr/bin/env python3
"""Fetch merge requests from a Launchpad user."""

import sys

from ubq import QueryService


def main():
    """Fetch and display merge requests from a Launchpad user."""
    if len(sys.argv) < 2:
        print("Usage: get_launchpad_merge_requests.py <launchpad_user_id>")
        print()
        print("Example: get_launchpad_merge_requests.py example-user")
        sys.exit(1)

    user_id = sys.argv[1]

    service = QueryService()
    service.login(provider_name="launchpad")

    merge_requests = service.get_merge_requests_from_user(
        user_id=user_id,
        provider_name="launchpad",
    )

    if not merge_requests:
        print(f"No merge requests found for user '{user_id}'.")
        return

    print(f"Merge requests for '{user_id}':")
    for mr in merge_requests:
        print(f"- ID: {mr.id}")
        print(f"  Status: {mr.status or 'N/A'}")
        print(f"  Source: {mr.source_branch or 'N/A'}")
        print(f"  Target: {mr.target_branch or 'N/A'}")
        print(f"  URL: {mr.web_url or 'N/A'}")


if __name__ == "__main__":
    main()
