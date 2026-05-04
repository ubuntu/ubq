"""Shared Launchpad provider base classes."""

from typing import Any

from launchpadlib.credentials import Credentials  # type: ignore[import-untyped]
from launchpadlib.launchpad import Launchpad  # type: ignore[import-untyped]

from ubq.models import AuthContext, AuthScope
from ubq.providers.provider import Provider
from ubq.providers.session import ProviderSession


class LaunchpadProvider(Provider):
    """Common Launchpad provider behavior shared by capability adapters."""

    provider_name: str = "launchpad"

    def __init__(self) -> None:
        self._launchpad: Launchpad | None = None

    def _get_lp_object(self) -> Launchpad:
        """Return the authenticated Launchpad session object or raise if not authenticated."""
        if self._launchpad is None:
            raise RuntimeError("Launchpad not yet authenticated. Run 'authenticate()' first.")

        return self._launchpad

    def _get_lp_ubuntu_distro_object(self) -> Any:
        """Fetch the Launchpad Ubuntu distribution object."""
        lp = self._get_lp_object()

        if not hasattr(lp, "distributions"):
            raise RuntimeError("Launchpad session does not have 'distributions' attribute.")

        return lp.distributions["ubuntu"]

    def _get_lp_debian_distro_object(self) -> Any:
        """Fetch the Launchpad Debian distribution object."""
        lp = self._get_lp_object()

        if not hasattr(lp, "distributions"):
            raise RuntimeError("Launchpad session does not have 'distributions' attribute.")

        return lp.distributions["debian"]

    def _get_lp_source_package_object(self, package_name: str) -> Any:
        """Fetch a Launchpad source package object by name."""
        try:
            return self._get_lp_ubuntu_distro_object().getSourcePackage(name=package_name)
        except KeyError:
            return None

    def authenticate(self, auth_context: AuthContext) -> ProviderSession:
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
        return self._launchpad

    def set_session_object(self, session_object: Any) -> None:
        """Set the underlying Launchpad session object."""
        if not isinstance(session_object, Launchpad):
            raise ValueError("Expected a Launchpad session object.")

        self._launchpad = session_object
