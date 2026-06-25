"""Integrity checks on the shipped upstream data file."""

import re
import unittest
from urllib.parse import urlparse

from ubq.providers.upstream.data_file import VALID_TYPES, load_sources

_OUT_OF_SCOPE_HOSTS = {"github.com", "api.github.com", "launchpad.net"}


class DataIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = load_sources()

    def test_file_is_non_empty(self) -> None:
        self.assertGreater(len(self.sources), 500)

    def test_all_types_in_scope(self) -> None:
        for source in self.sources.values():
            self.assertIn(source.type, VALID_TYPES)

    def test_no_out_of_scope_hosts(self) -> None:
        for source in self.sources.values():
            host = (urlparse(source.stable_url).hostname or "").lower()
            self.assertNotIn(host, _OUT_OF_SCOPE_HOSTS)

    def test_known_packages_present(self) -> None:
        for name in ("gnome-shell", "firefox", "freetype"):
            self.assertIn(name, self.sources)

    def test_every_entry_has_required_fields(self) -> None:
        for source in self.sources.values():
            self.assertTrue(source.stable_url)
            self.assertTrue(source.stable_regex)

    def test_tcl8_6_regex_rejects_compact_zip_version(self) -> None:
        source = self.sources["tcl8.6"]
        self.assertIsNone(re.search(source.stable_regex, "tcl8618-src.zip"))
        self.assertIsNotNone(re.search(source.stable_regex, "tcl8.6.18-src.tar.gz"))

    def test_some_entries_have_version_fixups(self) -> None:
        with_fixups = [s for s in self.sources.values() if s.version_fixups]
        self.assertGreater(len(with_fixups), 0)

    def test_cdparanoia_has_prepend_fixup(self) -> None:
        self.assertIn("cdparanoia", self.sources)
        self.assertIn("prepend:3.", self.sources["cdparanoia"].version_fixups)
