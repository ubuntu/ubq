# tests/upstream/test_versioning.py
"""Tests for upstream version comparison and fixups."""

import unittest

from ubq.providers.upstream.versioning import apply_fixups, compare_versions, max_version


class CompareVersionsTests(unittest.TestCase):
    def test_numeric_segments_compared_as_integers(self) -> None:
        self.assertLess(compare_versions("1.2.3", "1.10.0"), 0)

    def test_equal_versions(self) -> None:
        self.assertEqual(compare_versions("1.0", "1.0"), 0)

    def test_greater_version(self) -> None:
        self.assertGreater(compare_versions("2.0", "1.0"), 0)

    def test_tilde_sorts_before_release(self) -> None:
        self.assertLess(compare_versions("1.0~rc1", "1.0"), 0)
        self.assertLess(compare_versions("1.0~beta", "1.0~rc1"), 0)

    def test_plus_sorts_after_release(self) -> None:
        self.assertGreater(compare_versions("1.0+dfsg", "1.0"), 0)

    def test_letters_sort_after_digits_end(self) -> None:
        self.assertGreater(compare_versions("1.0a", "1.0"), 0)

    def test_none_and_empty_sort_lowest(self) -> None:
        self.assertLess(compare_versions("", "1.0"), 0)
        self.assertLess(compare_versions(None, "1.0"), 0)
        self.assertGreater(compare_versions("1.0", None), 0)


class MaxVersionTests(unittest.TestCase):
    def test_returns_larger(self) -> None:
        self.assertEqual(max_version("1.2.3", "1.10.0"), "1.10.0")

    def test_none_loses(self) -> None:
        self.assertEqual(max_version(None, "1.0"), "1.0")


class ApplyFixupsTests(unittest.TestCase):
    def test_single_substitution(self) -> None:
        self.assertEqual(apply_fixups("1-2-3", [r"sub:-=>."]), "1.2.3")

    def test_substitutions_applied_in_order(self) -> None:
        self.assertEqual(apply_fixups("rc1", [r"sub:rc=>~rc", r"sub:^=>1.0"]), "1.0~rc1")

    def test_no_fixups_returns_unchanged(self) -> None:
        self.assertEqual(apply_fixups("1.0", []), "1.0")

    def test_prepend(self) -> None:
        self.assertEqual(apply_fixups("1.2.3", ["prepend:3."]), "3.1.2.3")

    def test_append(self) -> None:
        self.assertEqual(apply_fixups("1.2.3", ["append:~dfsg"]), "1.2.3~dfsg")

    def test_drop_if_equal_match_returns_none(self) -> None:
        self.assertIsNone(apply_fixups("1.2.0~alpha1", ["drop_if_equal:1.2.0~alpha1"]))

    def test_drop_if_equal_no_match_unchanged(self) -> None:
        self.assertEqual(apply_fixups("1.2.1", ["drop_if_equal:1.2.0~alpha1"]), "1.2.1")

    def test_drop_short_circuits_later_ops(self) -> None:
        self.assertIsNone(apply_fixups("x", ["drop_if_equal:x", "append:y"]))

    def test_libreoffice_triplet(self) -> None:
        # legacy: v[0:5] + v[7:]; then if len>5 and v[5]=='.' insert '~'
        self.assertEqual(apply_fixups("5.3.0.2", ["libreoffice_triplet"]), "5.3.0")
        self.assertEqual(apply_fixups("5.3.0.2.alpha1", ["libreoffice_triplet"]), "5.3.0~alpha1")

    def test_mozjs_dots(self) -> None:
        self.assertEqual(apply_fixups("128", ["mozjs_dots"]), "1.2.8")
        self.assertEqual(apply_fixups("1", ["mozjs_dots"]), "1")

    def test_first_two_dotted(self) -> None:
        self.assertEqual(apply_fixups("30", ["first_two_dotted"]), "3.0")
        self.assertEqual(apply_fixups("3", ["first_two_dotted"]), "3")

    def test_underscore_to_dot_if_full(self) -> None:
        self.assertEqual(apply_fixups("1_2_3", ["underscore_to_dot_if_full"]), "1.2.3")
        # not a full match (leading non-digit) -> unchanged
        self.assertEqual(apply_fixups("v1_2", ["underscore_to_dot_if_full"]), "v1_2")

    def test_dash_to_dot_if_full(self) -> None:
        self.assertEqual(apply_fixups("1-2-3", ["dash_to_dot_if_full"]), "1.2.3")
        self.assertEqual(apply_fixups("1.2-rc1", ["dash_to_dot_if_full"]), "1.2-rc1")

    def test_gnome_prerelease_nonnumeric(self) -> None:
        self.assertEqual(apply_fixups("50.alpha", ["gnome_prerelease"]), "50~alpha")
        self.assertEqual(apply_fixups("3.38.beta", ["gnome_prerelease"]), "3.38~beta")

    def test_gnome_prerelease_numeric_unchanged(self) -> None:
        self.assertEqual(apply_fixups("50.1", ["gnome_prerelease"]), "50.1")

    def test_gnome_prerelease_no_match_unchanged(self) -> None:
        self.assertEqual(apply_fixups("abc", ["gnome_prerelease"]), "abc")

    def test_unknown_op_raises(self) -> None:
        with self.assertRaises(ValueError):
            apply_fixups("1.0", ["bogus:x"])
