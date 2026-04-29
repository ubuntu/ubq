#!/usr/bin/env python3
"""Fetch contents of a Launchpad bug by its ID."""

import sys

from lazr.restfulclient.errors import CredentialsFileError

from ubq.models import AuthScope, ProviderCredentials
from ubq.services import QueryService


def main():
    """Fetch and display a Launchpad bug."""
    if len(sys.argv) < 2:
        print("Usage: get_launchpad_bug.py <bug_id> [--credentials-file FILE]")
        print()
        print("Example: get_launchpad_bug.py 123456")
        print("Example: get_launchpad_bug.py 123456 --credentials-file credentials.oauth")
        sys.exit(1)

    bug_id = sys.argv[1]
    token = None

    # Extract credentials from file if provided
    if "--credentials-file" in sys.argv:
        cred_idx = sys.argv.index("--credentials-file")
        if cred_idx + 1 < len(sys.argv):
            cred_file = sys.argv[cred_idx + 1]
            with open(cred_file, "r") as f:
                token = f.read().strip()

    # Create service with default registry
    service = QueryService()

    # Authenticate to Launchpad
    try:
        service.login(
            provider_name="launchpad",
            scope=AuthScope.READ_ONLY,
            credentials=ProviderCredentials(token=token) if token else None,
        )
    except CredentialsFileError as e:
        print(f"Invalid credentials file: {e}", file=sys.stderr)
        sys.exit(1)

    # Now fetch the bug using the authenticated session
    bug = service.get_bug(
        bug_id=bug_id,
        provider_name="launchpad",
        scope=AuthScope.READ_ONLY,
        metadata_only=True,
    )

    if bug is None:
        print(f"Bug with ID {bug_id} not found.")
        sys.exit(1)
    else:
        print(f"Bug {bug_id}:")
        print(f"  Title: {getattr(bug, 'title', 'N/A')}")
        print(f"  Tags: {getattr(bug, 'tags', 'N/A')}")
        print(f"  Status: {getattr(bug, 'status', 'N/A')}")
        print(f"  Priority: {getattr(bug, 'priority', 'N/A')}")
        print(f"  Assignee: {getattr(bug, 'assignee', 'N/A')}")
        print(f"  Created At: {getattr(bug, 'created_at', 'N/A')}")
        print(f"  Updated At: {getattr(bug, 'updated_at', 'N/A')}")
        print(f"  Last Message At: {getattr(bug, 'last_message_at', 'N/A')}")
        print(f"  Last Patch At: {getattr(bug, 'last_patch_at', 'N/A')}")


if __name__ == "__main__":
    main()
