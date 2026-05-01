"""Common interface for all data providers."""

from typing import Any, Protocol, runtime_checkable

from ubq.models import AuthContext
from ubq.providers.session import ProviderSession


@runtime_checkable
class Provider(Protocol):
    """Base ubq provider class."""

    provider_name: str

    def authenticate(self, auth_context: AuthContext) -> ProviderSession:
        """Authenticate against provider and return a reusable session."""

    def get_session_object(self) -> Any:
        """Provide the object used to interact with a remote session if there is one."""

    def set_session_object(self, session_object: Any) -> None:
        """Set the object used to interact with a remote session if there is one."""
