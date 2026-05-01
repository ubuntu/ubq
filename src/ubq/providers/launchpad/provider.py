"""Shared Launchpad provider base classes."""

from typing import Any

from launchpadlib.credentials import Credentials  # type: ignore[import-untyped]
from launchpadlib.launchpad import Launchpad  # type: ignore[import-untyped]

from ubq.models import AuthContext, AuthScope
from ubq.providers.session import ProviderSession


class LaunchpadProvider:
    """Common Launchpad provider behavior shared by capability adapters."""

    provider_name = "launchpad"

    def __init__(self):
        self._launchpad = None

    def _check_authenticated(self) -> None:
        """Check if provider session is authenticated and raise if not."""
        if self._launchpad is None:
            raise RuntimeError("Launchpad not yet authenticated. Run 'authenticate()' first.")

    def _get_lp_source_package_object(self, package_name: str) -> Any:
        """Fetch a Launchpad source package object by name."""
        self._check_authenticated()

        try:
            return self._launchpad.distributions["ubuntu"].getSourcePackage(name=package_name)
        except KeyError:
            return None

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
            session_object=self._launchpad,
        ).with_provider(self)

    def get_session_object(self) -> Launchpad | None:
        """Return the underlying Launchpad session object if available."""
        self._check_authenticated()
        return self._launchpad

    def set_session_object(self, session_object: Any) -> None:
        """Set the underlying Launchpad session object."""
        if not isinstance(session_object, Launchpad):
            raise ValueError("Expected a Launchpad session object.")

        self._launchpad = session_object
