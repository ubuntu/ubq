"""Shared Launchpad provider base classes."""

from launchpadlib.credentials import Credentials  # type: ignore[import-untyped]
from launchpadlib.launchpad import Launchpad  # type: ignore[import-untyped]

from ubq.models import AuthContext, AuthScope
from ubq.providers.session import ProviderSession


class LaunchpadProvider:
    """Common Launchpad provider behavior shared by capability adapters."""

    provider_name = "launchpad"

    def __init__(self):
        self._launchpad = None

    def authenticate(self, auth_context: AuthContext) -> "ProviderSession":
        """Authenticate with Launchpad and return a reusable session."""
        if auth_context.credentials is not None and auth_context.credentials.token is not None:
            credentials = Credentials.from_string(auth_context.credentials.token)

            self._launchpad = Launchpad(
                credentials,
                None,
                None,
                service_root="production",
                version="devel",
            )

        else:
            access_levels = ["READ_PUBLIC"]

            if auth_context.scope == AuthScope.READ_WRITE:
                access_levels = ["WRITE_PRIVATE"]

            self._launchpad = Launchpad.login_with(
                application_name="ubq",
                service_root="production",
                allow_access_levels=access_levels,
                version="devel",
            )

        return ProviderSession(
            provider_name=self.provider_name,
            scope=auth_context.scope,
        ).with_provider(self)
