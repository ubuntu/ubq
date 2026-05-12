#!/usr/bin/env python3
"""Fetch GitHub pull requests for a user or by owner/repo#number identifier."""

import sys

from ubq import QueryService
from ubq.models import ProviderCredentials


def main():
    """Fetch and display GitHub pull requests."""
    if len(sys.argv) < 2:
        print("Usage: get_github_pull_requests.py <owner/repo#number | --user USERNAME>")
        print("                                   [--token TOKEN]")
        print()
        print("Example: get_github_pull_requests.py ubuntu/ubq#7")
        print("Example: get_github_pull_requests.py --user octocat")
        print("Example: get_github_pull_requests.py --user octocat --token ghp_...")
        sys.exit(1)

    token = None
    if "--token" in sys.argv:
        token_idx = sys.argv.index("--token")
        if token_idx + 1 < len(sys.argv):
            token = sys.argv[token_idx + 1]

    service = QueryService()
    service.login(
        provider_name="github",
        credentials=ProviderCredentials(token=token) if token else None,
    )

    if "--user" in sys.argv:
        user_idx = sys.argv.index("--user")
        if user_idx + 1 >= len(sys.argv):
            print("Error: --user requires a username argument.", file=sys.stderr)
            sys.exit(1)
        user_id = sys.argv[user_idx + 1]

        pull_requests = service.get_merge_requests_from_user(
            user_id=user_id,
            provider_name="github",
        )

        if not pull_requests:
            print(f"No pull requests found for user '{user_id}'.")
            return

        print(f"Pull requests for '{user_id}':")
        for pr in pull_requests:
            print(f"- ID: {pr.id}")
            print(f"  Title: {pr.title}")
            print(f"  Status: {pr.status or 'N/A'}")
            print(f"  Source: {pr.source_branch or 'N/A'}")
            print(f"  Target: {pr.target_branch or 'N/A'}")
            print(f"  URL: {pr.web_url or 'N/A'}")
            print(f"  Created At: {pr.created_at}")
            print(f"  Updated At: {pr.updated_at}")
    else:
        mr_id = sys.argv[1]

        pr = service.get_merge_request(
            merge_request_id=mr_id,
            provider_name="github",
        )

        if pr is None:
            print(f"Pull request '{mr_id}' not found.")
            sys.exit(1)

        print(f"Pull request {mr_id}:")
        print(f"  Title: {pr.title}")
        print(f"  Status: {pr.status or 'N/A'}")
        print(f"  Source: {pr.source_branch or 'N/A'}")
        print(f"  Target: {pr.target_branch or 'N/A'}")
        print(f"  URL: {pr.web_url or 'N/A'}")
        print(f"  Author: {pr.author.username if pr.author else 'N/A'}")
        print(f"  Created At: {pr.created_at}")
        print(f"  Updated At: {pr.updated_at}")
        print(f"  Merged At: {pr.merged_at}")


if __name__ == "__main__":
    main()
