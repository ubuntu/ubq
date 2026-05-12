#!/usr/bin/env python3
"""Search for Launchpad bugs using ubq QueryService."""

import sys
from datetime import datetime

from lazr.restfulclient.errors import CredentialsFileError

from ubq import QueryService
from ubq.models import AuthScope, BugSearchRecord, ProviderCredentials, UserRecord


def usage() -> None:
    print("Usage: search_launchpad_bugs.py [OPTIONS]")
    print()
    print("Optional:")
    print("  --title TEXT                  Search text")
    print("  --tag TAG                     Tag to match (repeatable)")
    print("  --owner USERNAME              Launchpad username of bug owner")
    print("  --assignee USERNAME           Launchpad username of assignee")
    print("  --milestone NAME              Milestone name")
    print("  --status STATUS               Bug status")
    print("  --importance IMPORTANCE       Bug importance")
    print("  --created-since YYYY-MM-DD    e.g. 2026-01-01")
    print("  --created-before YYYY-MM-DD   e.g. 2026-12-31")
    print("  --modified-since YYYY-MM-DD   e.g. 2026-01-01")
    print("  --credentials-file FILE       Path to OAuth credentials file")
    print()
    print("Examples:")
    print("  search_launchpad_bugs.py --title apport --status New")
    print("  search_launchpad_bugs.py --tag regression --importance High")


def parse_day(value: str) -> datetime:
    """Parse a date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as err:
        raise ValueError(f"Invalid date '{value}'. Expected YYYY-MM-DD format.") from err


def parse_args(argv: list[str]) -> dict[str, object]:
    """Parse command-line arguments for bug search."""
    args: dict[str, object] = {
        "title": None,
        "tags": [],
        "owner": None,
        "assignee": None,
        "milestone": None,
        "status": None,
        "importance": None,
        "created_since": None,
        "created_before": None,
        "modified_since": None,
        "credentials_file": None,
    }

    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg in ("-h", "--help"):
            usage()
            sys.exit(0)

        if arg == "--title":
            i += 1
            args["title"] = argv[i]
        elif arg == "--tag":
            i += 1
            tags = args["tags"]
            if isinstance(tags, list):
                tags.append(argv[i])
        elif arg == "--owner":
            i += 1
            args["owner"] = argv[i]
        elif arg == "--assignee":
            i += 1
            args["assignee"] = argv[i]
        elif arg == "--milestone":
            i += 1
            args["milestone"] = argv[i]
        elif arg == "--status":
            i += 1
            args["status"] = argv[i]
        elif arg == "--importance":
            i += 1
            args["importance"] = argv[i]
        elif arg == "--created-since":
            i += 1
            args["created_since"] = parse_day(argv[i])
        elif arg == "--created-before":
            i += 1
            args["created_before"] = parse_day(argv[i])
        elif arg == "--modified-since":
            i += 1
            args["modified_since"] = parse_day(argv[i])
        elif arg == "--credentials-file":
            i += 1
            args["credentials_file"] = argv[i]
        else:
            print(f"Unknown argument: {arg}", file=sys.stderr)
            usage()
            sys.exit(1)

        i += 1

    return args


def main() -> None:
    """Search Launchpad bugs and print matching records."""
    args = parse_args(sys.argv)

    token = None
    credentials_file = args["credentials_file"]
    if isinstance(credentials_file, str) and credentials_file:
        with open(credentials_file, "r") as handle:
            token = handle.read().strip()

    service = QueryService()

    try:
        service.login(
            provider_name="launchpad",
            scope=AuthScope.READ_ONLY,
            credentials=ProviderCredentials(token=token) if token else None,
        )
    except CredentialsFileError as err:
        print(f"Invalid credentials file: {err}", file=sys.stderr)
        sys.exit(1)

    owner = args["owner"]
    assignee = args["assignee"]

    query = BugSearchRecord(
        provider_name="launchpad",
        title=args["title"] if isinstance(args["title"], str) else None,
        tags=args["tags"] if isinstance(args["tags"], list) else [],
        owner=UserRecord(username=owner) if isinstance(owner, str) else None,
        assignee=UserRecord(username=assignee) if isinstance(assignee, str) else None,
        milestone=args["milestone"] if isinstance(args["milestone"], str) else None,
        status=args["status"] if isinstance(args["status"], str) else None,
        importance=args["importance"] if isinstance(args["importance"], str) else None,
        created_since=(
            args["created_since"] if isinstance(args["created_since"], datetime) else None
        ),
        created_before=(
            args["created_before"] if isinstance(args["created_before"], datetime) else None
        ),
        modified_since=(
            args["modified_since"] if isinstance(args["modified_since"], datetime) else None
        ),
    )

    try:
        bugs = service.search_bugs(
            query=query,
            provider_name="launchpad",
            scope=AuthScope.READ_ONLY,
        )
    except ValueError as err:
        print(f"Search failed: {err}", file=sys.stderr)
        sys.exit(1)

    if not bugs:
        print("No bugs found.")
        return

    print(f"Found {len(bugs)} bug(s):")
    for bug in bugs:
        print(f"- {bug.id}: {bug.title}")
        print(f"  Tags: {', '.join(bug.tags) if bug.tags else 'none'}")
        print(f"  Updated: {bug.updated_at}")


if __name__ == "__main__":
    main()
