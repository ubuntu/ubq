"""Tests for upstream fetch context and source handlers."""

import unittest

from ubq.errors import RequestTimeoutError
from ubq.providers.upstream.data_file import UpstreamSource
from ubq.providers.upstream.fetch import FetchContext
from ubq.providers.upstream.handlers import (
    descend_versioned_dir,
    extract_max_version,
    get_handler,
)


class FetchContextTests(unittest.TestCase):
    def test_uses_injected_opener(self) -> None:
        calls: list[str] = []

        def fake_opener(url: str, timeout: int) -> list[str]:
            calls.append(url)
            return ["line-a", "line-b"]

        ctx = FetchContext(timeout=5, opener=fake_opener)
        lines = ctx.get_lines("https://example.test/index")

        self.assertEqual(lines, ["line-a", "line-b"])
        self.assertEqual(calls, ["https://example.test/index"])

    def test_opener_timeout_becomes_request_timeout_error(self) -> None:
        def timing_out(url: str, timeout: int) -> list[str]:
            raise TimeoutError("slow")

        ctx = FetchContext(timeout=3, provider_name="upstream", opener=timing_out)
        with self.assertRaises(RequestTimeoutError):
            ctx.get_lines("https://example.test/")

    def test_opener_ioerror_returns_empty(self) -> None:
        def failing(url: str, timeout: int) -> list[str]:
            raise OSError("dns fail")

        ctx = FetchContext(opener=failing)
        self.assertEqual(ctx.get_lines("https://example.test/"), [])


def _source(**kwargs) -> UpstreamSource:
    base = dict(
        name="pkg",
        type="http",
        stable_url="https://example.test/releases/",
        stable_regex=r"pkg-([0-9.]+)\.tar\.xz",
    )
    base.update(kwargs)
    return UpstreamSource(**base)


class ExtractMaxVersionTests(unittest.TestCase):
    def test_picks_highest_version(self) -> None:
        lines = [
            '<a href="pkg-1.2.0.tar.xz">',
            '<a href="pkg-1.10.0.tar.xz">',
            '<a href="pkg-1.9.0.tar.xz">',
        ]
        self.assertEqual(extract_max_version(lines, r"pkg-([0-9.]+)\.tar\.xz", ()), "1.10.0")

    def test_no_match_returns_none(self) -> None:
        self.assertIsNone(extract_max_version(["nothing here"], r"pkg-([0-9.]+)", ()))

    def test_applies_fixups(self) -> None:
        lines = ["pkg-1-2-3.tar.xz"]
        self.assertEqual(
            extract_max_version(lines, r"pkg-([0-9-]+)\.tar\.xz", ("sub:-=>.",)), "1.2.3"
        )

    def test_dropped_candidate_is_skipped(self) -> None:
        lines = [
            '<a href="pkg-1.2.0.tar.xz">',
            '<a href="pkg-1.5.0.tar.xz">',
        ]
        # The would-be max (1.5.0) is dropped; 1.2.0 should win instead.
        self.assertEqual(
            extract_max_version(
                lines, r"pkg-([0-9.]+)\.tar\.xz", ("drop_if_equal:1.5.0",)
            ),
            "1.2.0",
        )

    def test_all_candidates_dropped_returns_none(self) -> None:
        lines = ['<a href="pkg-1.5.0.tar.xz">']
        self.assertIsNone(
            extract_max_version(lines, r"pkg-([0-9.]+)\.tar\.xz", ("drop_if_equal:1.5.0",))
        )


class DescendVersionedDirTests(unittest.TestCase):
    def test_descends_into_highest_subdir(self) -> None:
        def opener(url: str, timeout: int) -> list[str]:
            # parent listing of .../files/freetype2/
            return ['<a href="2.10/">', '<a href="2.13/">', '<a href="2.9/">']

        ctx = FetchContext(opener=opener)
        resolved = descend_versioned_dir(
            "https://sf.test/projects/freetype/files/freetype2/([0-9.]+)", ctx
        )
        self.assertEqual(resolved, "https://sf.test/projects/freetype/files/freetype2/2.13")

    def test_ignores_parent_directory_href(self) -> None:
        def opener(url: str, timeout: int) -> list[str]:
            return ['<a href="../">', '<a href="1.3/">', '<a href="1.4/">']

        ctx = FetchContext(opener=opener)
        resolved = descend_versioned_dir(
            "https://sf.test/projects/pkg/files/pkg/([0-9.]+)", ctx
        )
        self.assertEqual(resolved, "https://sf.test/projects/pkg/files/pkg/1.4")

    def test_plain_url_unchanged(self) -> None:
        ctx = FetchContext(opener=lambda u, t: [])
        url = "https://example.test/releases/"
        self.assertEqual(descend_versioned_dir(url, ctx), url)


class HandlerTests(unittest.TestCase):
    def test_http_handler_returns_max_version(self) -> None:
        def opener(url: str, timeout: int) -> list[str]:
            return ['<a href="pkg-2.0.tar.xz">', '<a href="pkg-2.5.tar.xz">']

        ctx = FetchContext(opener=opener)
        version = get_handler("http").fetch_version(_source(), ctx)
        self.assertEqual(version, "2.5")

    def test_every_valid_type_has_handler(self) -> None:
        from ubq.providers.upstream.data_file import VALID_TYPES

        for source_type in VALID_TYPES:
            self.assertIsNotNone(get_handler(source_type))

    def test_unknown_type_raises(self) -> None:
        with self.assertRaises(ValueError):
            get_handler("github")
