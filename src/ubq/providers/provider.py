"""Common interface for all data providers."""

from typing import Protocol, runtime_checkable

from ubq.models import AuthContext
from ubq.providers.session import ProviderSession


@runtime_checkable
class Provider(Protocol):
    """Base ubq provider class."""

    provider_name: str

    def authenticate(self, auth_context: AuthContext) -> "ProviderSession":
        """Authenticate against provider and return a reusable session."""
        ...
