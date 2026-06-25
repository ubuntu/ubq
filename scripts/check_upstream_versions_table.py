#!/usr/bin/env python3
"""Compare desktop versions-table upstream values with the ubq upstream provider."""

from __future__ import annotations

import argparse
import html
import sys
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser

from ubq import QueryService

DEFAULT_URL = "https://people.canonical.com/~platform/desktop/versions/versions.html"


@dataclass(frozen=True, slots=True)
class VersionRow:
    """One package row from the desktop versions table."""

    package: str
    upstream_version: str | None


class VersionsTableParser(HTMLParser):
    """Extract package names and upstream-version cells from the HTML table."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[VersionRow] = []
        self._in_row = False
        self._in_cell = False
        self._cells: list[str] = []
        self._current_cell: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            if self._in_cell:
                self._cells.append(_normalise_text("".join(self._current_cell)))
                self._current_cell = []
                self._in_cell = False
            if self._in_row:
                self._finish_row()
            self._in_row = True
            self._cells = []
        elif self._in_row and tag == "td":
            self._in_cell = True
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._in_cell:
            self._cells.append(_normalise_text("".join(self._current_cell)))
            self._current_cell = []
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            self._finish_row()
            self._in_row = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell.append(data)

    def _finish_row(self) -> None:
        if len(self._cells) < 4:
            return
        package = self._cells[0]
        if not package or package == "Package":
            return
        self.rows.append(
            VersionRow(
                package=package,
                upstream_version=_normalise_upstream_cell(self._cells[3]),
            )
        )


def _normalise_text(value: str) -> str:
    """Collapse HTML/unicode whitespace in table cell text."""
    return " ".join(html.unescape(value).replace("\xa0", " ").split())


def _normalise_upstream_cell(value: str) -> str | None:
    """Return a comparable upstream-version cell value, or ``None`` if missing."""
    normalised = _normalise_text(value)
    if not normalised or normalised == "UNKNOWN":
        return None
    return normalised


def _accepted_versions(value: str) -> set[str]:
    """Return acceptable provider versions for one table upstream-version value."""
    return {part.strip() for part in value.split("/") if part.strip()}


def fetch_rows(url: str) -> list[VersionRow]:
    """Fetch and parse the desktop versions HTML table."""
    request = urllib.request.Request(url, headers={"User-Agent": "ubq/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", errors="replace")
    parser = VersionsTableParser()
    parser.feed(body)
    return parser.rows


def compare_rows(
    rows: list[VersionRow],
    service: QueryService,
    package_filter: set[str] | None = None,
    limit: int | None = None,
    verbose: bool = False,
) -> int:
    """Compare table rows with the upstream provider and return mismatch count."""
    checked = 0
    matched = 0
    mismatched = 0
    skipped_table = 0
    skipped_provider = 0
    errors = 0

    for row in rows:
        if package_filter is not None and row.package not in package_filter:
            continue
        if limit is not None and checked >= limit:
            break
        if row.upstream_version is None:
            skipped_table += 1
            continue

        try:
            provider_version = service.get_version(
                package_name=row.package,
                archive="",
                series="",
                pocket=None,
                provider_name="upstream",
            )
        except Exception as exc:  # noqa: BLE001 - keep validating the remaining packages.
            errors += 1
            print(f"ERROR {row.package}: {exc}")
            continue
        if provider_version is None:
            skipped_provider += 1
            if verbose:
                print(f"SKIP provider-missing {row.package}: table={row.upstream_version}")
            continue

        checked += 1
        upstream_value = provider_version.version_string
        accepted = _accepted_versions(row.upstream_version)
        if upstream_value in accepted:
            matched += 1
            if verbose:
                print(f"OK   {row.package}: {upstream_value}")
        else:
            mismatched += 1
            print(
                f"DIFF {row.package}: provider={upstream_value!r} "
                f"table={row.upstream_version!r}"
            )

    print()
    print(f"Rows parsed: {len(rows)}")
    print(f"Compared: {checked}")
    print(f"Matched: {matched}")
    print(f"Mismatched: {mismatched}")
    print(f"Errors: {errors}")
    print(f"Skipped table missing/UNKNOWN: {skipped_table}")
    print(f"Skipped provider missing/out-of-scope: {skipped_provider}")
    return mismatched


def main() -> int:
    """Run the table comparison script."""
    parser = argparse.ArgumentParser(
        description="Compare desktop versions table upstream values with ubq upstream."
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="versions.html URL to fetch")
    parser.add_argument(
        "--package",
        action="append",
        dest="packages",
        help="package to compare; may be supplied more than once",
    )
    parser.add_argument("--limit", type=int, help="maximum number of comparable rows to check")
    parser.add_argument("--verbose", action="store_true", help="print OK and skip rows")
    args = parser.parse_args()

    rows = fetch_rows(args.url)
    service = QueryService()
    service.login(provider_name="upstream")

    mismatches = compare_rows(
        rows=rows,
        service=service,
        package_filter=set(args.packages) if args.packages else None,
        limit=args.limit,
        verbose=args.verbose,
    )
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
