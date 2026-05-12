#!/usr/bin/env python3
"""Fetch version of a deb package in Debian Unstable and Ubuntu Resolute."""

import sys

from ubq import QueryService


def main():
    """Fetch and display Ubuntu package version information."""
    if len(sys.argv) < 2:
        print("Usage: get_ubuntu_package_version.py <package_name>")
        print()
        print("Example: get_ubuntu_package_version.py bash")
        sys.exit(1)

    package_name = sys.argv[1]

    # Create service with default registry
    service = QueryService()
    service.login(provider_name="launchpad")

    # Fetch the package version information
    ubuntu_version = service.get_version(
        package_name=package_name,
        series="resolute",
        pocket="Release",
        provider_name="launchpad",
    )

    debian_version = service.get_version(
        package_name=package_name,
        series="debian-unstable",
        pocket="Release",
        provider_name="launchpad",
    )

    print(f"Package Name: {package_name}")

    if ubuntu_version is not None:
        print(f"Ubuntu version: {ubuntu_version.version_string}")
    else:
        print("Ubuntu version not found.")

    if debian_version is not None:
        print(f"Debian version: {debian_version.version_string}")
    else:
        print("Debian version not found.")


if __name__ == "__main__":
    main()
