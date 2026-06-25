"""Shared base class for the upstream provider."""

from typing import Any

from ubq.models import AuthContext
from ubq.providers.session import ProviderSession
from ubq.providers.upstream.data_file import UpstreamSource, load_sources
from ubq.providers.upstream.fetch import FetchContext


class UpstreamProvider:
    """Common upstream provider behavior shared by capability adapters."""

    provider_name: str = "upstream"

    def __init__(
        self,
        timeout: int = 30,
        sources: dict[str, UpstreamSource] | None = None,
        fetch_context: FetchContext | None = None,
    ) -> None:
        self._timeout = timeout
        self._sources = sources if sources is not None else load_sources()
        self._fetch_context = fetch_context or FetchContext(
            timeout=timeout, provider_name=self.provider_name
        )
        self._session_object: Any = None

    def _get_source(self, name: str) -> UpstreamSource | None:
        return self._sources.get(name)

    def authenticate(self, auth_context: AuthContext) -> ProviderSession:
        """Return a session; the upstream provider needs no credentials."""
        return ProviderSession(
            provider_name=self.provider_name,
            session_object=None,
        ).with_provider(self)

    def get_session_object(self) -> Any:
        """Return the (unused) session object."""
        return self._session_object

    def set_session_object(self, session_object: Any) -> None:
        """Store the (unused) session object."""
        self._session_object = session_object
