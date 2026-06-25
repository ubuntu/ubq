"""Tests for the upstream provider capability classes."""

import unittest

from ubq.models import AuthContext, PackageRecord, VersionRecord
from ubq.providers.upstream.data_file import UpstreamSource
from ubq.providers.upstream.fetch import FetchContext
from ubq.providers.upstream.package import UpstreamPackageProvider
from ubq.providers.upstream.version import UpstreamVersionProvider

_SOURCES = {
    "coreutils": UpstreamSource(
        name="coreutils",
        type="gnu",
        stable_url="https://ftpmirror.gnu.org/gnu/coreutils",
        stable_regex=r"coreutils-([0-9.]+)\.tar\.xz",
        project_url="https://www.gnu.org/software/coreutils/",
    )
}


def _opener_for(versions: list[str]):
    def opener(url: str, timeout: int) -> list[str]:
        return [f'<a href="coreutils-{v}.tar.xz">' for v in versions]

    return opener


class UpstreamPackageProviderTests(unittest.TestCase):
    def test_get_package_returns_record(self) -> None:
        provider = UpstreamPackageProvider(
            sources=_SOURCES, fetch_context=FetchContext(opener=lambda u, t: [])
        )
        record = provider.get_package("coreutils", "ubuntu")
        self.assertIsInstance(record, PackageRecord)
        self.assertEqual(record.name, "coreutils")
        self.assertEqual(record.provider_name, "upstream")
        self.assertEqual(record.package_url, "https://www.gnu.org/software/coreutils/")

    def test_get_package_unknown_returns_none(self) -> None:
        provider = UpstreamPackageProvider(
            sources=_SOURCES, fetch_context=FetchContext(opener=lambda u, t: [])
        )
        self.assertIsNone(provider.get_package("does-not-exist", "ubuntu"))


class UpstreamVersionProviderTests(unittest.TestCase):
    def test_get_version_returns_max_version(self) -> None:
        provider = UpstreamVersionProvider(
            sources=_SOURCES,
            fetch_context=FetchContext(opener=_opener_for(["9.1", "9.10", "9.2"])),
        )
        record = provider.get_version("coreutils", "ubuntu", "n/a", None)
        self.assertIsInstance(record, VersionRecord)
        self.assertEqual(record.version_string, "9.10")
        self.assertEqual(record.package_name, "coreutils")
        self.assertEqual(record.provider_name, "upstream")

    def test_get_version_unknown_returns_none(self) -> None:
        provider = UpstreamVersionProvider(
            sources=_SOURCES, fetch_context=FetchContext(opener=lambda u, t: [])
        )
        self.assertIsNone(provider.get_version("nope", "ubuntu", "n/a", None))

    def test_get_version_no_match_returns_none(self) -> None:
        provider = UpstreamVersionProvider(
            sources=_SOURCES, fetch_context=FetchContext(opener=lambda u, t: ["unrelated"])
        )
        self.assertIsNone(provider.get_version("coreutils", "ubuntu", "n/a", None))


class AuthenticateTests(unittest.TestCase):
    def test_authenticate_returns_session_with_capability(self) -> None:
        provider = UpstreamPackageProvider(
            sources=_SOURCES, fetch_context=FetchContext(opener=lambda u, t: [])
        )
        session = provider.authenticate(AuthContext(provider_name="upstream"))
        self.assertEqual(session.provider_name, "upstream")
        self.assertIs(session.get_package_provider(), provider)


class RegistryIntegrationTests(unittest.TestCase):
    def test_upstream_reachable_via_query_service(self) -> None:
        from ubq import QueryService
        from ubq.providers import ProviderRegistry

        package_provider = UpstreamPackageProvider(
            sources=_SOURCES, fetch_context=FetchContext(opener=lambda u, t: [])
        )
        version_provider = UpstreamVersionProvider(
            sources=_SOURCES, fetch_context=FetchContext(opener=_opener_for(["9.4"]))
        )
        registry = ProviderRegistry(providers=[package_provider, version_provider])
        service = QueryService(registry=registry)
        service.login(provider_name="upstream")

        self.assertIn("upstream", service.available_providers())
        package = service.get_package(
            package_name="coreutils", archive="ubuntu", provider_name="upstream"
        )
        version = service.get_version(
            package_name="coreutils",
            archive="ubuntu",
            series="n/a",
            pocket=None,
            provider_name="upstream",
        )
        self.assertEqual(package.name, "coreutils")
        self.assertEqual(version.version_string, "9.4")

    def test_default_registry_includes_upstream(self) -> None:
        from ubq.providers import ProviderRegistry

        self.assertIn("upstream", ProviderRegistry().available_provider_names())
