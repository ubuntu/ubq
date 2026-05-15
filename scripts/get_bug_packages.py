#!/usr/bin/env python3
"""Fetch all packages affected by a Launchpad bug."""

import sys

from lazr.restfulclient.errors import CredentialsFileError

from ubq import QueryService
from ubq.models import ProviderCredentials


def main():
    """Fetch and display packages affected by a Launchpad bug."""
    if len(sys.argv) < 2:
        print("Usage: get_bug_packages.py <bug_id> [--credentials-file FILE]")
        print()
        print("Example: get_bug_packages.py 123456")
        print("Example: get_bug_packages.py 123456 --credentials-file credentials.oauth")
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
            credentials=ProviderCredentials(token=token) if token else None,
        )
    except CredentialsFileError as e:
        print(f"Invalid credentials file: {e}", file=sys.stderr)
        sys.exit(1)

    # Fetch the bug (metadata only, no comments needed)
    bug = service.get_bug(
        bug_id=bug_id,
        provider_name="launchpad",
        metadata_only=False,
    )

    if bug is None:
        print(f"Bug with ID {bug_id} not found.")
        sys.exit(1)

    packages = [task.package_name for task in bug.bug_tasks if task.package_name is not None]

    if not packages:
        print(f"No packages found for bug {bug_id}.")
    else:
        print(f"Packages affected by bug {bug_id}:")
        for package in packages:
            print(f"  {package}")


if __name__ == "__main__":
    main()
