#!/usr/bin/env python3
"""Submit a bug to Launchpad."""

import sys

from lazr.restfulclient.errors import CredentialsFileError

from ubq.models import AuthScope, ProviderCredentials, UserRecord
from ubq.models.bug import BugSubmissionRecord
from ubq.services import QueryService


def usage():
    print("Usage: submit_lp_bug.py --title TITLE --package PACKAGE [OPTIONS]")
    print()
    print("Required:")
    print("  --title TITLE                  Bug title")
    print("  --package PACKAGE              Affected package (repeatable)")
    print()
    print("Optional:")
    print("  --description TEXT             Bug description")
    print("  --importance IMPORTANCE        e.g. Critical, High, Medium, Low, Wishlist")
    print("  --status STATUS                e.g. New, Confirmed, In Progress, Fix Committed")
    print("  --tag TAG                      Bug tag (repeatable)")
    print("  --milestone MILESTONE          Milestone name")
    print("  --assignee USERNAME            Launchpad username to assign the bug to")
    print("  --subscriber USERNAME          Launchpad username to subscribe (repeatable)")
    print("  --private                      Mark bug as private")
    print("  --credentials-file FILE        Path to OAuth credentials file")
    print()
    print("Examples:")
    print("  submit_lp_bug.py --title 'Crash on startup' --package mypackage")
    print("  submit_lp_bug.py --title 'Crash' --package pkg1 --package pkg2 \\")
    print("                   --description 'It crashes' --importance High --private")


def parse_args(argv: list[str]) -> dict:
    args: dict = {
        "title": None,
        "packages": [],
        "description": None,
        "importance": None,
        "status": None,
        "tags": [],
        "milestone": None,
        "assignee": None,
        "subscribers": [],
        "private": False,
        "credentials_file": None,
    }

    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg in ("-h", "--help"):
            usage()
            sys.exit(0)
        elif arg == "--title":
            i += 1
            args["title"] = argv[i]
        elif arg == "--package":
            i += 1
            args["packages"].append(argv[i])
        elif arg == "--description":
            i += 1
            args["description"] = argv[i]
        elif arg == "--importance":
            i += 1
            args["importance"] = argv[i]
        elif arg == "--status":
            i += 1
            args["status"] = argv[i]
        elif arg == "--tag":
            i += 1
            args["tags"].append(argv[i])
        elif arg == "--milestone":
            i += 1
            args["milestone"] = argv[i]
        elif arg == "--assignee":
            i += 1
            args["assignee"] = argv[i]
        elif arg == "--subscriber":
            i += 1
            args["subscribers"].append(argv[i])
        elif arg == "--private":
            args["private"] = True
        elif arg == "--credentials-file":
            i += 1
            args["credentials_file"] = argv[i]
        else:
            print(f"Unknown argument: {arg}", file=sys.stderr)
            usage()
            sys.exit(1)
        i += 1

    return args


def main():
    """Submit a bug to Launchpad."""
    args = parse_args(sys.argv)

    if not args["title"]:
        print("Error: --title is required.", file=sys.stderr)
        usage()
        sys.exit(1)

    if not args["packages"]:
        print("Error: at least one --package is required.", file=sys.stderr)
        usage()
        sys.exit(1)

    token = None
    if args["credentials_file"]:
        with open(args["credentials_file"], "r") as f:
            token = f.read().strip()

    service = QueryService()

    try:
        service.login(
            provider_name="launchpad",
            scope=AuthScope.READ_WRITE,
            credentials=ProviderCredentials(token=token) if token else None,
        )
    except CredentialsFileError as e:
        print(f"Invalid credentials file: {e}", file=sys.stderr)
        sys.exit(1)

    packages = [
        service.get_package(pkg, "launchpad", AuthScope.READ_WRITE) for pkg in args["packages"]
    ]

    assignee = UserRecord(username=args["assignee"]) if args["assignee"] else None
    subscribers = [UserRecord(username=u) for u in args["subscribers"]]

    submission = BugSubmissionRecord(
        provider_name="launchpad",
        title=args["title"],
        packages=packages,
        description=args["description"],
        importance=args["importance"],
        status=args["status"],
        tags=args["tags"],
        milestone=args["milestone"],
        assignee=assignee,
        subscribers=subscribers,
        private=args["private"],
    )

    bug = service.submit_bug(submission=submission, provider_name="launchpad")

    if bug is None:
        print("Bug submission failed.", file=sys.stderr)
        sys.exit(1)

    print(f"Bug submitted successfully!")
    print(f"  ID:    {bug.id}")
    print(f"  Title: {bug.title}")
    print(f"  Tags:  {bug.tags}")
    if bug.bug_tasks:
        print(f"  Tasks:")
        for task in bug.bug_tasks:
            print(f"    - {task.title} [{task.status} / {task.importance}]")


if __name__ == "__main__":
    main()
