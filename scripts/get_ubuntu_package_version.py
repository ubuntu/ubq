#!/usr/bin/env python3
"""Fetch version of a deb package in Debian Unstable and Ubuntu Resolute."""

import sys

from ubq import QueryService


def main():
    """Fetch and display Ubuntu package version information."""
    if len(sys.argv) < 2:
        print("Usage: get_ubuntu_package_version.py <package_name> [ubuntu_series]")
        print()
        print("Example: get_ubuntu_package_version.py bash resolute")
        sys.exit(1)

    package_name = sys.argv[1]
    ubuntu_series = sys.argv[2] if len(sys.argv) > 2 else "resolute"

    # Create service with default registry
    service = QueryService()
    service.login(provider_name="launchpad")

    # Fetch the package version information
    ubuntu_version = service.get_version(
        package_name=package_name,
        archive="ubuntu",
        series=ubuntu_series,
        pocket="Release",
        provider_name="launchpad",
    )

    debian_version = service.get_version(
        package_name=package_name,
        archive="debian",
        series="sid",
        pocket="Release",
        provider_name="launchpad",
    )

    print(f"Package Name: {package_name}")

    if ubuntu_version is not None:
        print(f"Ubuntu version ({ubuntu_series}): {ubuntu_version.version_string}")
    else:
        print(f"Ubuntu version not found for series '{ubuntu_series}'.")

    if debian_version is not None:
        print(f"Debian version: {debian_version.version_string}")
    else:
        print("Debian version not found.")


if __name__ == "__main__":
    main()
