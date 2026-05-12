"""Shared GitHub provider base class."""

import json
import os
import subprocess
import urllib.parse
import urllib.request
from typing import Any

from ubq.models import AuthContext
from ubq.providers.session import ProviderSession

GH_GRAPHQL_URL = "https://api.github.com/graphql"
GH_API_URL = "https://api.github.com"
GH_BASE_URL = "https://github.com"


def _get_github_token() -> str | None:
    """Return a GitHub token from GITHUB_TOKEN env var or the gh CLI, or None."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


class GitHubProvider:
    """Common GitHub provider behavior shared by capability adapters."""

    provider_name: str = "github"

    def __init__(self) -> None:
        self._token: str | None = None

    def _make_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _graphql(self, query: str, variables: dict) -> dict:
        """Execute a GitHub GraphQL query and return parsed response data."""
        payload = json.dumps({"query": query, "variables": variables}).encode()
        req = urllib.request.Request(
            GH_GRAPHQL_URL,
            data=payload,
            headers=self._make_headers(),
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        if errors := data.get("errors"):
            raise RuntimeError(f"GitHub GraphQL errors: {errors}")
        return data["data"]

    def _rest_get(self, path: str, params: dict | None = None) -> Any:
        """Perform a REST GET request to the GitHub API."""
        url = f"{GH_API_URL}{path}"
        if params:
            query_str = urllib.parse.urlencode(params)
            url = f"{url}?{query_str}"
        req = urllib.request.Request(url, headers=self._make_headers(), method="GET")
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def _rest_post(self, path: str, body: dict) -> Any:
        """Perform a REST POST request to the GitHub API."""
        url = f"{GH_API_URL}{path}"
        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            url, data=payload, headers=self._make_headers(), method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def authenticate(self, auth_context: AuthContext) -> ProviderSession:
        """Authenticate with GitHub and return a reusable session."""
        if auth_context.credentials is not None and auth_context.credentials.token is not None:
            self._token = auth_context.credentials.token
        else:
            self._token = _get_github_token()

        return ProviderSession(
            provider_name=self.provider_name,
            scope=auth_context.scope,
            session_object=self._token,
        )

    def get_session_object(self) -> Any:
        """Return the GitHub token used for authentication."""
        return self._token

    def set_session_object(self, session_object: Any) -> None:
        """Set the GitHub token."""
        self._token = session_object
