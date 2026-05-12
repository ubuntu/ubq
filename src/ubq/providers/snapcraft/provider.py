"""Shared Snapcraft provider base class."""

import json
import os
import urllib.request
from typing import Any

from ubq.models import AuthContext
from ubq.providers.session import ProviderSession

SNAPCRAFT_API_BASE = "https://api.snapcraft.io/v2"
SNAPCRAFT_STORE_BASE = "https://snapcraft.io"
_SNAP_DEVICE_SERIES = "16"
_USER_AGENT = "ubq/1.0"


def _get_snapcraft_token() -> str | None:
    """Return a Snapcraft macaroon from the SNAPCRAFT_STORE_AUTH environment variable."""
    return os.environ.get("SNAPCRAFT_STORE_AUTH")


class SnapcraftProvider:
    """Common Snapcraft provider behavior shared by capability adapters."""

    provider_name: str = "snapcraft"

    def __init__(self) -> None:
        self._macaroon: str | None = None

    def _make_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Snap-Device-Series": _SNAP_DEVICE_SERIES,
            "User-Agent": _USER_AGENT,
        }
        if self._macaroon:
            headers["Authorization"] = (
                self._macaroon
                if self._macaroon.startswith("Macaroon ")
                else f"Macaroon {self._macaroon}"
            )
        return headers

    def _rest_get(self, path: str, params: dict[str, str] | None = None) -> Any:
        """Perform a REST GET request to the Snapcraft API."""
        url = f"{SNAPCRAFT_API_BASE}{path}"
        if params:
            query_str = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query_str}"
        req = urllib.request.Request(url, headers=self._make_headers(), method="GET")
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def authenticate(self, auth_context: AuthContext) -> ProviderSession:
        """Authenticate with Snapcraft and return a reusable session."""
        if auth_context.credentials is not None and auth_context.credentials.token is not None:
            self._macaroon = auth_context.credentials.token
        else:
            self._macaroon = _get_snapcraft_token()

        return ProviderSession(
            provider_name=self.provider_name,
            session_object=self._macaroon,
        ).with_provider(self)

    def get_session_object(self) -> Any:
        """Return the Snapcraft macaroon token used for authentication."""
        return self._macaroon

    def set_session_object(self, session_object: Any) -> None:
        """Set the Snapcraft macaroon token."""
        self._macaroon = session_object
