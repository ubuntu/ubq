#!/usr/bin/env python3
"""Fetch a GitHub issue by its owner/repo#number identifier."""

import sys

from ubq import QueryService
from ubq.models import ProviderCredentials


def main():
    """Fetch and display a GitHub issue."""
    if len(sys.argv) < 2:
        print("Usage: get_github_issue.py <owner/repo#number> [--show-comments] [--token TOKEN]")
        print()
        print("Example: get_github_issue.py ubuntu/ubq#42")
        print("Example: get_github_issue.py ubuntu/ubq#42 --show-comments")
        print("Example: get_github_issue.py ubuntu/ubq#42 --token ghp_...")
        sys.exit(1)

    bug_id = sys.argv[1]
    token = None

    if "--token" in sys.argv:
        token_idx = sys.argv.index("--token")
        if token_idx + 1 < len(sys.argv):
            token = sys.argv[token_idx + 1]

    show_comments = "--show-comments" in sys.argv

    service = QueryService()
    service.login(
        provider_name="github",
        credentials=ProviderCredentials(token=token) if token else None,
    )

    bug = service.get_bug(
        bug_id=bug_id,
        provider_name="github",
        metadata_only=not show_comments,
    )

    if bug is None:
        print(f"Issue '{bug_id}' not found.")
        sys.exit(1)

    print(f"Issue {bug_id}:")
    print(f"  Title: {bug.title}")
    print(f"  Tags: {bug.tags}")
    print(f"  Owner: {getattr(bug.owner, 'username', 'N/A') if bug.owner else 'N/A'}")
    print(f"  Assignee: {getattr(bug.assignee, 'username', 'N/A') if bug.assignee else 'N/A'}")
    print(f"  Created At: {bug.created_at}")
    print(f"  Updated At: {bug.updated_at}")

    if show_comments and bug.comments:
        print("  Comments:")
        for comment in bug.comments:
            author = comment.author.display_name if comment.author else "N/A"
            print(f"    - {author}: {comment.content}")


if __name__ == "__main__":
    main()
