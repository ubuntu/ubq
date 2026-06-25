"""Loading and validation of the upstream package data file."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

VALID_TYPES = frozenset(
    {"gnome", "gitlab", "sourceforge", "gnu", "kde", "gstreamer", "pypi", "cpan", "http", "ftp"}
)

_DEFAULT_DATA_PATH = Path(__file__).parent / "data" / "packages.toml"


@dataclass(frozen=True, slots=True)
class UpstreamSource:
    """A single package's upstream source definition."""

    name: str
    type: str
    stable_url: str
    stable_regex: str
    unstable_url: str | None = None
    unstable_regex: str | None = None
    tags: tuple[str, ...] = ()
    flavors: tuple[str, ...] = ()
    version_fixups: tuple[str, ...] = ()
    project_url: str | None = None


def parse_source(name: str, raw: dict) -> UpstreamSource:
    """Validate and build an :class:`UpstreamSource` from one raw TOML entry."""
    source_type = raw.get("type")
    if source_type not in VALID_TYPES:
        raise ValueError(
            f"Package '{name}' has unknown or out-of-scope type {source_type!r}. "
            f"Valid types: {', '.join(sorted(VALID_TYPES))}."
        )
    for required in ("stable_url", "stable_regex"):
        if not raw.get(required):
            raise ValueError(f"Package '{name}' is missing required field '{required}'.")
    return UpstreamSource(
        name=name,
        type=source_type,
        stable_url=raw["stable_url"],
        stable_regex=raw["stable_regex"],
        unstable_url=raw.get("unstable_url"),
        unstable_regex=raw.get("unstable_regex"),
        tags=tuple(raw.get("tags", ())),
        flavors=tuple(raw.get("flavors", ())),
        version_fixups=tuple(raw.get("version_fixups", ())),
        project_url=raw.get("project_url"),
    )


def load_sources(path: str | None = None) -> dict[str, UpstreamSource]:
    """Load all upstream sources from the data file, validating each entry."""
    data_path = Path(path) if path is not None else _DEFAULT_DATA_PATH
    with data_path.open("rb") as handle:
        raw_data = tomllib.load(handle)
    return {name: parse_source(name, entry) for name, entry in raw_data.items()}
