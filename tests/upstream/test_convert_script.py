# tests/upstream/test_convert_script.py
"""Tests for the legacy->TOML conversion logic."""

import importlib.util
import io
import re
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "convert_upstream_packages.py"
_spec = importlib.util.spec_from_file_location("convert_upstream_packages", _SCRIPT)
convert_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(convert_mod)


class ClassifyTests(unittest.TestCase):
    def test_gnome_download_host(self) -> None:
        self.assertEqual(
            convert_mod.classify("https://download.gnome.org/sources/x/50", r"x-([0-9.]+)"),
            "gnome",
        )

    def test_gitlab_host(self) -> None:
        self.assertEqual(
            convert_mod.classify("https://gitlab.freedesktop.org/a/b/tags", r"v([0-9.]+)"),
            "gitlab",
        )

    def test_sourceforge_host(self) -> None:
        self.assertEqual(
            convert_mod.classify("https://sourceforge.net/projects/x/files/y", r"x-([0-9.]+)"),
            "sourceforge",
        )

    def test_pypi_libraries_io(self) -> None:
        self.assertEqual(
            convert_mod.classify(
                "https://libraries.io/pypi/x/versions", r'href="/pypi/x/([0-9.]+)"'
            ),
            "pypi",
        )

    def test_ftp_scheme(self) -> None:
        self.assertEqual(
            convert_mod.classify("ftp://ftp.alsa-project.org/pub/lib/", r"alsa-lib-([0-9.]+)"),
            "ftp",
        )

    def test_unknown_host_defaults_to_http(self) -> None:
        self.assertEqual(
            convert_mod.classify("https://example.test/releases/", r"x-([0-9.]+)"), "http"
        )


class ScopeTests(unittest.TestCase):
    def test_sentinels_out_of_scope(self) -> None:
        self.assertFalse(convert_mod.is_in_scope("DEBIAN"))
        self.assertFalse(convert_mod.is_in_scope("UBUNTU"))
        self.assertFalse(convert_mod.is_in_scope("UNTRACKED"))

    def test_github_host_out_of_scope(self) -> None:
        self.assertFalse(
            convert_mod.is_in_scope(("https://api.github.com/repos/a/b/tags", r"v([0-9.]+)"))
        )

    def test_launchpad_host_out_of_scope(self) -> None:
        self.assertFalse(
            convert_mod.is_in_scope(("https://launchpad.net/x/+download", r"x-([0-9.]+)"))
        )

    def test_third_party_in_scope(self) -> None:
        self.assertTrue(
            convert_mod.is_in_scope(("https://download.gnome.org/sources/x/50", r"x-([0-9.]+)"))
        )


class EntryToTomlDictTests(unittest.TestCase):
    def test_tcl8_6_regex_requires_dotted_version(self) -> None:
        entry = convert_mod.entry_to_toml_dict(
            "tcl8.6",
            (
                "https://sourceforge.net/projects/tcl/files/Tcl/(8.6.[0-9.]+)",
                r"tcl([0-9][0-9.]*)-src\.(?:tar\.(?:gz|bz2|xz|lz)|tgz|zip)+",
            ),
            None,
            [],
            ["ubuntu"],
        )
        self.assertIsNone(re.search(entry["stable_regex"], "tcl8618-src.zip"))
        self.assertIsNotNone(re.search(entry["stable_regex"], "tcl8.6.18-src.tar.gz"))


_GLOBALS = ["underscore_to_dot_if_full", "dash_to_dot_if_full"]


class FixupsForTests(unittest.TestCase):
    """Pin the legacy sanitize_version -> fixup-op mapping."""

    def test_plain_package_globals_only(self) -> None:
        self.assertEqual(
            convert_mod.fixups_for("coreutils", "https://example.test/releases/"),
            _GLOBALS,
        )

    def test_cdparanoia_prepends(self) -> None:
        fixups = convert_mod.fixups_for("cdparanoia", "https://example.test/releases/")
        self.assertEqual(fixups, ["prepend:3.", *_GLOBALS])

    def test_aalib_sub_rc_to_p(self) -> None:
        self.assertEqual(
            convert_mod.fixups_for("aalib", "https://example.test/releases/"),
            ["sub:rc=>p", *_GLOBALS],
        )

    def test_libtheora_drop(self) -> None:
        self.assertEqual(
            convert_mod.fixups_for("libtheora", "https://example.test/releases/"),
            ["drop_if_equal:1.2.0~alpha1", *_GLOBALS],
        )

    def test_jackd2_appends_dfsg(self) -> None:
        self.assertEqual(
            convert_mod.fixups_for("jackd2", "https://example.test/releases/"),
            [*_GLOBALS, "append:~dfsg"],
        )

    def test_imagemagick_dash_after_globals(self) -> None:
        self.assertEqual(
            convert_mod.fixups_for("imagemagick", "https://example.test/releases/"),
            [*_GLOBALS, "sub:-=>."],
        )

    def test_mozjs_exact_includes_dots(self) -> None:
        self.assertEqual(
            convert_mod.fixups_for("mozjs", "https://example.test/releases/"),
            ["sub:\\.rc=>~rc", *_GLOBALS, "mozjs_dots"],
        )

    def test_mozjs_prefixed_no_dots(self) -> None:
        self.assertEqual(
            convert_mod.fixups_for("mozjs128", "https://example.test/releases/"),
            ["sub:\\.rc=>~rc", *_GLOBALS],
        )

    def test_zip_first_two_dotted(self) -> None:
        self.assertEqual(
            convert_mod.fixups_for("zip", "https://example.test/releases/"),
            [*_GLOBALS, "first_two_dotted"],
        )

    def test_gnome_host_appends_prerelease(self) -> None:
        fixups = convert_mod.fixups_for(
            "gnome-shell", "https://download.gnome.org/sources/gnome-shell/50"
        )
        self.assertEqual(fixups, [*_GLOBALS, "gnome_prerelease"])

    def test_gnome_gitlab_host_appends_prerelease(self) -> None:
        fixups = convert_mod.fixups_for(
            "aisleriot", "https://gitlab.gnome.org/GNOME/aisleriot/tags"
        )
        self.assertEqual(fixups, [*_GLOBALS, "gnome_prerelease"])


class TomlKeyQuotingTests(unittest.TestCase):
    """Pin TOML table-header serialization for tricky package names."""

    def test_plus_name_is_quoted(self) -> None:
        self.assertFalse(convert_mod._is_bare_key("dvd+rw-tools"))
        self.assertEqual(convert_mod._toml_header("dvd+rw-tools"), '["dvd+rw-tools"]')

    def test_dot_name_is_quoted(self) -> None:
        self.assertFalse(convert_mod._is_bare_key("gtk+2.0"))
        self.assertEqual(convert_mod._toml_header("gtk+2.0"), '["gtk+2.0"]')
        self.assertFalse(convert_mod._is_bare_key("boost1.88"))
        self.assertEqual(convert_mod._toml_header("boost1.88"), '["boost1.88"]')

    def test_bare_name_is_unquoted(self) -> None:
        self.assertTrue(convert_mod._is_bare_key("gtk4"))
        self.assertEqual(convert_mod._toml_header("gtk4"), "[gtk4]")
        self.assertTrue(convert_mod._is_bare_key("gtk-doc"))
        self.assertEqual(convert_mod._toml_header("gtk-doc"), "[gtk-doc]")

    def test_tricky_key_round_trips_through_tomllib(self) -> None:
        name = "gtk+2.0"
        mapping = {
            name: {
                "type": "http",
                "stable_url": "https://example.test/releases/",
                "stable_regex": r"x-([0-9.]+)",
                "tags": [],
                "flavors": ["ubuntu"],
            }
        }
        parsed = tomllib.loads(convert_mod._dump_toml(mapping))
        self.assertIn(name, parsed)
        self.assertEqual(parsed[name]["type"], "http")


class ArgumentParserTests(unittest.TestCase):
    def test_help_uses_argparse_usage(self) -> None:
        stdout = io.StringIO()
        with self.assertRaises(SystemExit) as ctx, redirect_stdout(stdout):
            convert_mod.main(["-h"])

        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("usage:", stdout.getvalue())
        self.assertIn("legacy_path", stdout.getvalue())
        self.assertIn("out_path", stdout.getvalue())

    def test_missing_args_use_argparse_error(self) -> None:
        stderr = io.StringIO()
        with self.assertRaises(SystemExit) as ctx, redirect_stderr(stderr):
            convert_mod.main([])

        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("usage:", stderr.getvalue())
        self.assertIn("legacy_path", stderr.getvalue())
