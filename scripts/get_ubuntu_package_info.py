#!/usr/bin/env python3
"""Fetch contents of a Launchpad package by its name."""

import sys

from ubq import QueryService
from ubq.models import AuthScope


def main():
    """Fetch and display Ubuntu package information."""
    if len(sys.argv) < 2:
        print("Usage: get_ubuntu_package_info.py <package_name>")
        print()
        print("Example: get_ubuntu_package_info.py bash")
        sys.exit(1)

    package_name = sys.argv[1]

    # Create service with default registry
    service = QueryService()
    service.login(provider_name="launchpad", scope=AuthScope.READ_ONLY)

    # Fetch the package information
    package = service.get_package(
        package_name=package_name,
        provider_name="launchpad",
        scope=AuthScope.READ_ONLY,
    )

    if package is None:
        print(f"Package '{package_name}' not found.")
        sys.exit(1)

    print(f"Package Name: {package.name}")
    print(f"URL: {package.package_url}")


if __name__ == "__main__":
    main()
