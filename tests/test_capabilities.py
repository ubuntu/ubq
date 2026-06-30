"""Unit tests for QueryService capability introspection."""

import unittest

from ubq import QueryService
from ubq.providers import ProviderRegistry


class CapabilityIntrospectionTests(unittest.TestCase):
    """capabilities()/supports() report what a provider can do, pre-login."""

    def setUp(self) -> None:
        # Use the default registry (real providers) so the matrix is meaningful.
        self.service = QueryService(registry=ProviderRegistry())

    def test_launchpad_supports_all_four_capabilities(self) -> None:
        caps = self.service.capabilities("launchpad")
        self.assertEqual({"bug", "version", "package", "merge_request"}, set(caps))

    def test_snapcraft_supports_only_version_and_package(self) -> None:
        caps = self.service.capabilities("snapcraft")
        self.assertEqual({"version", "package"}, set(caps))

    def test_github_supports_bug_and_merge_request_only(self) -> None:
        caps = self.service.capabilities("github")
        self.assertEqual({"bug", "merge_request"}, set(caps))

    def test_supports_true_for_available_capability(self) -> None:
        self.assertTrue(self.service.supports("snapcraft", "version"))

    def test_supports_false_for_unavailable_capability(self) -> None:
        # Snapcraft has no bug capability.
        self.assertFalse(self.service.supports("snapcraft", "bug"))

    def test_capabilities_work_without_login(self) -> None:
        # No login() called in setUp; this must still return data.
        self.assertIn("bug", self.service.capabilities("launchpad"))

    def test_unknown_provider_raises_valueerror(self) -> None:
        with self.assertRaises(ValueError):
            self.service.capabilities("does-not-exist")

    def test_supports_unknown_provider_raises_valueerror(self) -> None:
        with self.assertRaises(ValueError):
            self.service.supports("does-not-exist", "bug")

    def test_supports_unknown_capability_returns_false(self) -> None:
        # An unknown capability name is simply unsupported, not an error.
        self.assertFalse(self.service.supports("launchpad", "telepathy"))
