#!/usr/bin/env python3
"""Fetch a single Launchpad merge request by author, project, branch, and id."""

import sys

from ubq import QueryService


def main():
    """Fetch and display a single Launchpad merge request."""
    if len(sys.argv) < 2:
        print(
            "Usage: get_launchpad_merge_request.py "
            "<~author/project/branch/+merge/id>"
        )
        print()
        print(
            "Example: get_launchpad_merge_request.py "
            "~example-user/example-project/main/+merge/12345"
        )
        sys.exit(1)

    identifier = sys.argv[1].strip("/")

    try:
        author_part, rest = identifier.split("/", 1)
        author = author_part.lstrip("~")
        project, branch, merge_marker, merge_request_id = rest.rsplit("/", 3)
        if merge_marker != "+merge":
            raise ValueError
    except ValueError:
        print(
            f"Error: invalid identifier '{sys.argv[1]}'. "
            "Expected '~author/project/branch/+merge/id'.",
            file=sys.stderr,
        )
        sys.exit(1)

    service = QueryService()
    service.login(provider_name="launchpad")

    merge_request = service.get_merge_request(
        author=author,
        project=project,
        branch=branch,
        merge_request_id=merge_request_id,
        provider_name="launchpad",
    )

    if merge_request is None:
        print(f"Merge request '{sys.argv[1]}' not found.")
        sys.exit(1)

    print(f"Merge request {merge_request.id}:")
    print(f"  Status: {merge_request.status or 'N/A'}")
    print(f"  Source: {merge_request.source_branch or 'N/A'}")
    print(f"  Target: {merge_request.target_branch or 'N/A'}")
    print(f"  URL: {merge_request.web_url or 'N/A'}")
    print(f"  Created At: {merge_request.created_at}")
    print(f"  Merged At: {merge_request.merged_at}")
    print(
        f"  Added lines: "
        f"{merge_request.added_lines if merge_request.added_lines is not None else 'N/A'}"
    )
    print(
        f"  Removed lines: "
        f"{merge_request.removed_lines if merge_request.removed_lines is not None else 'N/A'}"
    )

    if merge_request.votes:
        print("  Votes:")
        for vote in merge_request.votes:
            print(f"    - {vote.voter.username}: {vote.vote or 'N/A'}")


if __name__ == "__main__":
    main()
