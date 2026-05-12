"""Query service unit tests."""

import unittest
from datetime import datetime

from ubq.models import (
    AuthContext,
    AuthScope,
    BugRecord,
    BugSearchRecord,
    BugSubmissionRecord,
    MergeRequestRecord,
    PackageRecord,
    VersionRecord,
)
from ubq.providers import (
    BugProvider,
    MergeRequestProvider,
    PackageProvider,
    ProviderSession,
    VersionProvider,
)
from ubq.services import ProviderRegistry, QueryService


class FakeProvider(BugProvider, PackageProvider, VersionProvider, MergeRequestProvider):
    """Fake provider class that provides all data types."""

    provider_name = "fake"

    def __init__(self) -> None:
        now = datetime(2026, 1, 1)
        package = PackageRecord(
            provider_name=self.provider_name,
            name="test-package",
            package_url="https://example.local/packages/test-package",
        )

        self._session_object = None
        self.auth_calls: list[AuthContext] = []
        self.metadata_bug_calls: list[str] = []
        self.full_bug_calls: list[str] = []
        self.search_bug_calls: list[BugSearchRecord] = []
        self.package_calls: list[str] = []
        self.version_calls: list[tuple[str, str]] = []
        self.merge_request_calls: list[str] = []
        self.assigned_merge_request_calls: list[str] = []
        self.submissions: list[BugSubmissionRecord] = []

        self._bugs: dict[str, BugRecord] = {
            "1": BugRecord(
                provider_name=self.provider_name,
                id="1",
                title="Bug one",
                description="Details",
                tags=["triage"],
                created_at=now,
                updated_at=now,
            )
        }
        self._packages: dict[str, PackageRecord] = {"test-package": package}
        self._versions: dict[tuple[str, str, str], VersionRecord] = {
            ("test-package", "resolute", "Release"): VersionRecord(
                provider_name=self.provider_name,
                version_string="1.2.3",
                package_name=package.name,
                series="resolute",
                pocket="Release",
                created_at=now,
                released_at=now,
            )
        }
        self._merge_requests: dict[str, MergeRequestRecord] = {
            "17": MergeRequestRecord(
                provider_name=self.provider_name,
                id="17",
                title="Fix bug one",
                description="MR details",
                status="open",
                source_branch="fix/bug-one",
                target_branch="main",
            )
        }

    def authenticate(self, auth_context: AuthContext) -> ProviderSession:
        self.auth_calls.append(auth_context)
        self._session_object = {
            "provider": auth_context.provider_name,
            "scope": auth_context.scope.value,
        }
        return ProviderSession(
            provider_name=self.provider_name,
            scope=auth_context.scope,
            session_object=self._session_object,
        ).with_provider(self)

    def get_session_object(self):
        return self._session_object

    def set_session_object(self, session_object):
        self._session_object = session_object

    def get_bug_metadata(self, bug_id: str) -> BugRecord | None:
        self.metadata_bug_calls.append(bug_id)
        return self._bugs.get(bug_id)

    def get_bug(self, bug_id: str) -> BugRecord | None:
        self.full_bug_calls.append(bug_id)
        return self._bugs.get(bug_id)

    def search_bugs(self, query: BugSearchRecord) -> list[BugRecord]:
        self.search_bug_calls.append(query)
        results = list(self._bugs.values())

        if query.title is None:
            return results

        needle = query.title.lower()
        return [bug for bug in results if needle in bug.title.lower()]

    def submit_bug(self, submission: BugSubmissionRecord) -> BugRecord | None:
        self.submissions.append(submission)
        bug_id = str(len(self._bugs) + 1)
        created = BugRecord(
            provider_name=self.provider_name,
            id=bug_id,
            title=submission.title,
            description=submission.description,
            tags=submission.tags,
        )
        self._bugs[bug_id] = created
        return created

    def get_version(self, package_name: str, series: str, pocket: str) -> VersionRecord | None:
        self.version_calls.append((package_name, series, pocket))
        return self._versions.get((package_name, series, pocket))

    def get_package(self, package_name: str) -> PackageRecord | None:
        self.package_calls.append(package_name)
        return self._packages.get(package_name)

    def get_merge_request(self, merge_request_id: str) -> MergeRequestRecord | None:
        self.merge_request_calls.append(merge_request_id)
        return self._merge_requests.get(merge_request_id)

    def get_merge_requests_from_user(self, user_id: str) -> list[MergeRequestRecord]:
        self.assigned_merge_request_calls.append(user_id)
        return list(self._merge_requests.values())


class QueryServiceTests(unittest.TestCase):
    """Validate query service behavior against a deterministic provider."""

    def setUp(self) -> None:
        self.provider = FakeProvider()
        registry = ProviderRegistry(providers=[self.provider])
        self.service = QueryService(registry=registry)

    def test_login_reuses_session_without_force(self) -> None:
        self.service.login(provider_name="fake")
        self.service.login(provider_name="fake")

        self.assertEqual(1, len(self.provider.auth_calls))
        self.assertEqual(AuthScope.READ_ONLY, self.provider.auth_calls[0].scope)

    def test_login_with_force_reauthenticates(self) -> None:
        self.service.login(provider_name="fake")
        self.service.login(provider_name="fake", force=True)

        self.assertEqual(2, len(self.provider.auth_calls))

    def test_get_bug_supports_full_and_metadata_paths(self) -> None:
        self.service.login(provider_name="fake")

        metadata_bug = self.service.get_bug(
            bug_id="1",
            provider_name="fake",
            metadata_only=True,
        )
        full_bug = self.service.get_bug(
            bug_id="1",
            provider_name="fake",
            metadata_only=False,
        )

        self.assertIsNotNone(metadata_bug)
        self.assertIsNotNone(full_bug)
        self.assertEqual(["1"], self.provider.metadata_bug_calls)
        self.assertEqual(["1"], self.provider.full_bug_calls)

    def test_service_requires_login_before_queries(self) -> None:
        with self.assertRaises(ValueError):
            self.service.get_bug(bug_id="1", provider_name="fake")

    def test_get_package_version_and_merge_request(self) -> None:
        self.service.login(provider_name="fake")

        package = self.service.get_package(package_name="test-package", provider_name="fake")
        version = self.service.get_version(
            package_name="test-package",
            series="resolute",
            pocket="Release",
            provider_name="fake",
        )
        merge_request = self.service.get_merge_request(
            merge_request_id="17",
            provider_name="fake",
        )

        self.assertIsNotNone(package)
        self.assertIsNotNone(version)
        self.assertIsNotNone(merge_request)
        self.assertEqual(["test-package"], self.provider.package_calls)
        self.assertEqual([("test-package", "resolute", "Release")], self.provider.version_calls)
        self.assertEqual(["17"], self.provider.merge_request_calls)

    def test_get_merge_requests_from_user(self) -> None:
        self.service.login(provider_name="fake")

        merge_requests = self.service.get_merge_requests_from_user(
            user_id="alice",
            provider_name="fake",
        )

        self.assertEqual(1, len(merge_requests))
        self.assertEqual(["alice"], self.provider.assigned_merge_request_calls)

    def test_submit_bug_uses_read_write_scope(self) -> None:
        submission = BugSubmissionRecord(
            provider_name="fake",
            title="new bug",
            package_names=["test-package"],
            description="submission body",
            tags=["test"],
        )

        with self.assertRaises(ValueError):
            self.service.submit_bug(submission=submission, provider_name="fake")

        self.service.login(provider_name="fake", scope=AuthScope.READ_WRITE)
        created = self.service.submit_bug(submission=submission, provider_name="fake")

        self.assertIsNotNone(created)
        self.assertEqual("new bug", created.title)
        self.assertEqual([submission], self.provider.submissions)
        self.assertEqual(AuthScope.READ_WRITE, self.provider.auth_calls[-1].scope)

    def test_search_bugs(self) -> None:
        self.service.login(provider_name="fake")

        query = BugSearchRecord(
            provider_name="fake",
            title="bug one",
        )
        matches = self.service.search_bugs(query=query, provider_name="fake")

        self.assertEqual(1, len(matches))
        self.assertEqual("1", matches[0].id)
        self.assertEqual([query], self.provider.search_bug_calls)

    def test_available_providers(self) -> None:
        self.assertEqual(("fake",), self.service.available_providers())
