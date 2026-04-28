"""Shared Launchpad provider base classes."""

from ubq.models import AuthContext
from ubq.providers.session import ProviderSession


class LaunchpadProvider:
    """Common Launchpad provider behavior shared by capability adapters."""

    provider_name = "launchpad"

    def authenticate(self, auth_context: AuthContext) -> ProviderSession:
        """Authenticate with Launchpad and return a reusable session."""
        return ProviderSession(
            provider_name=self.provider_name,
            scope=auth_context.scope,
        ).with_provider(self)
