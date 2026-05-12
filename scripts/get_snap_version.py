#!/usr/bin/env python3
"""Fetch the version of a snap package from Snapcraft for a given channel."""

import sys

from ubq import QueryService


def main():
    """Fetch and display snap package version information."""
    if len(sys.argv) < 3:
        print("Usage: get_snap_version.py <snap_name> <channel>")
        print()
        print("The channel format is <track>/<risk>, e.g. latest/stable or 1.0/beta.")
        print()
        print("Example: get_snap_version.py firefox latest/stable")
        sys.exit(1)

    snap_name = sys.argv[1]
    channel = sys.argv[2]

    channel_parts = channel.split("/", 1)
    if len(channel_parts) == 2:
        series, pocket = channel_parts
    else:
        series, pocket = channel, None

    # Create service with default registry
    service = QueryService()
    service.login(provider_name="snapcraft")

    version = service.get_version(
        package_name=snap_name,
        series=series,
        pocket=pocket,
        provider_name="snapcraft",
    )

    if version is None:
        print(f"No version found for snap '{snap_name}' on channel '{channel}'.")
        sys.exit(1)

    channel_label = f"{version.series}/{version.pocket}" if version.pocket else version.series
    print(f"Snap Name: {version.package_name}")
    print(f"Channel: {channel_label}")
    print(f"Version: {version.version_string}")


if __name__ == "__main__":
    main()
