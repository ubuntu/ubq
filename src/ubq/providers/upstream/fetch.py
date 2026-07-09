"""HTTP/FTP fetching for upstream source handlers."""

import urllib.error
import urllib.request
from collections.abc import Callable

from ubq.errors import RequestTimeoutError

_USER_AGENT = "ubq/1.0"


def _default_opener(url: str, timeout: int) -> list[str]:
    """Fetch *url* and return its body split into decoded lines."""
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    return data.decode("utf-8", errors="ignore").split("\n")


class FetchContext:
    """Shared fetch helper passed to source handlers."""

    def __init__(
        self,
        timeout: int = 30,
        provider_name: str = "upstream",
        opener: Callable[[str, int], list[str]] | None = None,
    ) -> None:
        self._timeout = timeout
        self._provider_name = provider_name
        self._opener = opener or _default_opener

    def get_lines(self, url: str) -> list[str]:
        """Fetch a URL and return decoded lines, or ``[]`` on non-timeout failure."""
        try:
            return self._opener(url, self._timeout)
        except TimeoutError as exc:
            raise RequestTimeoutError(self._provider_name, self._timeout) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise RequestTimeoutError(self._provider_name, self._timeout) from exc
            return []
        except OSError:
            return []
