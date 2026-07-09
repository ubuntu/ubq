"""Tests for upstream data-file parsing and validation."""

import tempfile
import unittest
from pathlib import Path

from ubq.providers.upstream.data_file import (
    VALID_TYPES,
    UpstreamSource,
    load_sources,
    parse_source,
)


class ParseSourceTests(unittest.TestCase):
    def test_parses_full_entry(self) -> None:
        src = parse_source(
            "gnome-shell",
            {
                "type": "gnome",
                "stable_url": "https://download.gnome.org/sources/gnome-shell/50",
                "stable_regex": r"gnome-shell-([0-9.]+)\.tar\.xz",
                "tags": ["gnome"],
                "flavors": ["ubuntu"],
                "project_url": "https://gitlab.gnome.org/GNOME/gnome-shell",
            },
        )
        self.assertEqual(src.name, "gnome-shell")
        self.assertEqual(src.type, "gnome")
        self.assertEqual(src.tags, ("gnome",))
        self.assertEqual(src.flavors, ("ubuntu",))
        self.assertIsNone(src.unstable_url)

    def test_unknown_type_raises_naming_package(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_source("bad", {"type": "github", "stable_url": "x", "stable_regex": "y"})
        self.assertIn("bad", str(ctx.exception))

    def test_missing_required_field_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_source("nourl", {"type": "gnu", "stable_regex": "y"})
        self.assertIn("nourl", str(ctx.exception))

    def test_valid_types_excludes_out_of_scope(self) -> None:
        for excluded in ("github", "launchpad", "debian", "ubuntu", "untracked"):
            self.assertNotIn(excluded, VALID_TYPES)


class LoadSourcesTests(unittest.TestCase):
    def test_loads_from_explicit_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            toml_path = Path(tmp) / "p.toml"
            toml_path.write_text(
                "[coreutils]\n"
                'type = "gnu"\n'
                'stable_url = "https://ftpmirror.gnu.org/gnu/coreutils"\n'
                'stable_regex = "coreutils-([0-9.]+)\\\\.tar\\\\.xz"\n'
                "tags = []\n"
                'flavors = ["ubuntu"]\n'
            )
            sources = load_sources(str(toml_path))
        self.assertIn("coreutils", sources)
        self.assertIsInstance(sources["coreutils"], UpstreamSource)

    def test_default_path_loads_shipped_file(self) -> None:
        sources = load_sources()
        self.assertGreater(len(sources), 0)
