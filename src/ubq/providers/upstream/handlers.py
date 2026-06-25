# src/ubq/providers/upstream/handlers.py
"""Source-type handlers that fetch the latest upstream version."""

import re
from typing import Protocol

from ubq.providers.upstream.data_file import VALID_TYPES, UpstreamSource
from ubq.providers.upstream.fetch import FetchContext
from ubq.providers.upstream.versioning import apply_fixups, compare_versions, max_version

_TRAILING_REGEX_SEG = re.compile(r"\([^/]*\)\s*$")
_HREF = re.compile(r'href=[\'"]([^\'"]+)[\'"]')


def extract_max_version(lines: list[str], regex: str, fixups: tuple[str, ...]) -> str | None:
    """Return the highest version matched by *regex* (group 1) across *lines*."""
    pattern = re.compile(regex)
    best: str | None = None
    for line in lines:
        for match in pattern.finditer(line):
            candidate = apply_fixups(match.group(1), list(fixups))
            if candidate is None:
                continue
            best = max_version(best, candidate)
    return best


def descend_versioned_dir(url: str, ctx: FetchContext) -> str:
    """Resolve a URL whose final path segment is a version regex.

    For e.g. ``.../files/freetype2/([0-9.]+)`` this fetches the parent listing,
    selects the highest-versioned matching subdirectory, and returns the
    concrete URL. URLs without a trailing regex segment are returned unchanged.
    """
    parent, sep, last = url.rpartition("/")
    if not sep or not _TRAILING_REGEX_SEG.search(last):
        return url
    seg_pattern = re.compile(f"^{last}$")
    best_name: str | None = None
    best_version: str | None = None
    for line in ctx.get_lines(parent + "/"):
        for href_match in _HREF.finditer(line):
            href = href_match.group(1).rstrip("/").rsplit("/", 1)[-1]
            seg_match = seg_pattern.match(href)
            if not seg_match:
                continue
            version = seg_match.group(1)
            if not any(char.isdigit() for char in version):
                continue
            if compare_versions(version, best_version) > 0:
                best_version = version
                best_name = href
    if best_name is None:
        return url
    return f"{parent}/{best_name}"


class SourceHandler(Protocol):
    """Contract for fetching the latest upstream version for a source."""

    def fetch_version(self, source: UpstreamSource, ctx: FetchContext) -> str | None: ...


class DirectoryHandler:
    """Fetch a listing/page, optionally descend a versioned dir, regex the version.

    This single implementation serves every in-scope source type. The distinct
    ``type`` values are retained for provenance and to allow future per-type
    divergence without touching the data file.
    """

    def fetch_version(self, source: UpstreamSource, ctx: FetchContext) -> str | None:
        resolved_url = descend_versioned_dir(source.stable_url, ctx)
        lines = ctx.get_lines(resolved_url)
        return extract_max_version(lines, source.stable_regex, source.version_fixups)


_DIRECTORY_HANDLER = DirectoryHandler()
HANDLERS: dict[str, SourceHandler] = {
    source_type: _DIRECTORY_HANDLER for source_type in VALID_TYPES
}


def get_handler(source_type: str) -> SourceHandler:
    """Return the handler for a source type, or raise ``ValueError`` if unknown."""
    try:
        return HANDLERS[source_type]
    except KeyError as exc:
        raise ValueError(f"No upstream handler for source type '{source_type}'.") from exc
