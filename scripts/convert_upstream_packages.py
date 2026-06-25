#!/usr/bin/env python3
"""Convert the legacy ubuntu-desktop-versions package map to packages.toml.

Usage:
    uv run scripts/convert_upstream_packages.py \
        ../ubuntu-desktop-versions/packages.py \
        src/ubq/providers/upstream/data/packages.toml

The legacy data uses bare tuples and helper functions. This script imports the
legacy module, calls those helpers (which yield concrete ``(url, regex)``
pairs), classifies each by URL host, drops out-of-scope sources
(github/launchpad/debian/ubuntu/untracked), merges per-flavor membership, and
emits a typed TOML data file.
"""

import argparse
import importlib.util
import sys
from urllib.parse import urlparse

OUT_OF_SCOPE_HOSTS = {"github.com", "api.github.com", "launchpad.net"}
_SENTINELS = {"DEBIAN", "UBUNTU", "UNTRACKED"}
_FLAVOR_LISTS = {
    "ubuntu": "ubuntu_package_info",
    "kubuntu": "kubuntu_package_info",
    "lubuntu": "lubuntu_package_info",
    "xubuntu": "xubuntu_package_info",
}


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _classify_host(host: str) -> str | None:
    """Map a URL host to a source type, or None if undecided."""
    matched: str | None = None
    if "download.gnome.org" in host or "gitlab.gnome.org" in host:
        matched = "gnome"
    elif host.startswith(("gitlab.", "salsa.")) or "freedesktop" in host or "xorg" in host:
        matched = "gitlab"
    elif "sourceforge" in host:
        matched = "sourceforge"
    elif "gnu.org" in host or "ftpmirror.gnu" in host:
        matched = "gnu"
    elif "download.kde.org" in host or "kde.org" in host:
        matched = "kde"
    elif "gstreamer" in host:
        matched = "gstreamer"
    return matched


def classify(stable_url: str, stable_regex: str) -> str:
    """Map a concrete (url, regex) pair to an in-scope source type."""
    host = _host(stable_url)
    by_host = _classify_host(host)
    if by_host is not None:
        return by_host
    if "libraries.io" in host and "/pypi/" in stable_url:
        return "pypi"
    if "libraries.io" in host and "/cpan/" in stable_url:
        return "cpan"
    if urlparse(stable_url).scheme == "ftp":
        return "ftp"
    return "http"


def is_in_scope(entry: object) -> bool:
    """Return True if the legacy stable-url entry is an in-scope third-party source."""
    if isinstance(entry, str):
        return entry not in _SENTINELS
    if isinstance(entry, (tuple, list)) and entry:
        return _host(str(entry[0])) not in OUT_OF_SCOPE_HOSTS
    return False


_GLOBAL_FIXUPS = ["underscore_to_dot_if_full", "dash_to_dot_if_full"]


def fixups_for(name: str, stable_url: str) -> list[str]:
    """Return ordered version-fixup ops for a package, reproducing legacy order.

    The two global ops (underscored/dashed normalization) are applied to every
    package for fidelity with the legacy ``sanitize_version``. Per-package ops
    bracket the globals exactly as the legacy code applied them, and gnome-host
    entries get a trailing ``gnome_prerelease`` op.
    """
    fixups: list[str] = []

    # Per-package ops that legacy applied BEFORE the global underscored/dashed.
    if name == "libtheora":
        fixups.append("drop_if_equal:1.2.0~alpha1")
    if name == "cdparanoia":
        fixups.append("prepend:3.")
    if name == "aalib":
        fixups.append("sub:rc=>p")
    if name == "mawk":
        fixups.append("prepend:1.3.4.")
    if name == "portaudio19":
        fixups.append("prepend:19+svn")
    if name == "luasocket":
        fixups.append("sub:-=>~")
    if name == "osinfo-db":
        fixups.append("prepend:0.")
    if name in ("libreoffice", "libreoffice-dictionaries"):
        fixups.append("libreoffice_triplet")
    if name.startswith("mozjs"):
        fixups.append("sub:\\.rc=>~rc")
    if name == "ntp":
        fixups.append("sub:p=>.p")

    # Global underscored/dashed normalization (legacy applied this to everyone).
    fixups.extend(_GLOBAL_FIXUPS)

    # Per-package ops that legacy applied AFTER the globals.
    if name == "imagemagick":
        fixups.append("sub:-=>.")
    if name == "mozjs":
        fixups.append("mozjs_dots")
    if name == "libopenmpt":
        fixups.append("sub:-beta=>~beta")
    if name in ("zip", "unzip"):
        fixups.append("first_two_dotted")
    # ghostscript is out of scope (github package, excluded); only jackd2 here.
    if name == "jackd2":
        fixups.append("append:~dfsg")

    # GNOME pre-release normalization, conditioned on the matched URL host.
    if "gnome.org" in stable_url:
        fixups.append("gnome_prerelease")

    return fixups


def _stable_regex_for(name: str, stable_regex: str) -> str:
    """Return package-specific corrected regexes that differ from legacy data."""
    if name == "tcl8.6":
        # Avoid matching the compact zip filename (tcl8618-src.zip) as version
        # 8618; only dotted source archive versions are comparable here.
        return (
            r"tcl([0-9][0-9.]*\.[0-9][0-9.]*)-src"
            r"\.(?:tar\.(?:gz|bz2|xz|lz)|tgz|zip)+"
        )
    return stable_regex


def entry_to_toml_dict(
    name: str,
    stable: tuple,
    unstable: object,
    tags: list,
    flavors: list,
) -> dict:
    """Build a TOML entry dict for one in-scope package."""
    stable_url, stable_regex = stable[0], stable[1]
    stable_regex = _stable_regex_for(name, stable_regex)
    result: dict = {
        "type": classify(stable_url, stable_regex),
        "stable_url": stable_url,
        "stable_regex": stable_regex,
        "tags": list(tags),
        "flavors": sorted(flavors),
        "version_fixups": fixups_for(name, stable_url),
    }
    if isinstance(unstable, (tuple, list)) and len(unstable) >= 2:
        result["unstable_url"] = unstable[0]
        result["unstable_regex"] = unstable[1]
    return result


def _load_legacy(legacy_path: str):
    spec = importlib.util.spec_from_file_location("legacy_packages", legacy_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load legacy packages module from {legacy_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def convert(legacy_path: str) -> dict[str, dict]:
    """Build the full {name: toml_dict} mapping from the legacy module."""
    module = _load_legacy(legacy_path)
    by_name: dict[str, tuple] = {}
    flavor_membership: dict[str, set[str]] = {}

    for flavor, attr in _FLAVOR_LISTS.items():
        for name, stable, unstable, _sourcetags in getattr(module, attr, []):
            if not is_in_scope(stable):
                continue
            flavor_membership.setdefault(name, set()).add(flavor)
            if name not in by_name:
                by_name[name] = (stable, unstable, _sourcetags)

    output: dict[str, dict] = {}
    for name, (stable, unstable, sourcetags) in by_name.items():
        output[name] = entry_to_toml_dict(
            name, stable, unstable, sourcetags, list(flavor_membership[name])
        )
    return output


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _is_bare_key(name: str) -> bool:
    """True if name is a valid TOML bare key (A-Za-z0-9_- only, non-empty)."""
    return bool(name) and all(c.isalnum() or c in "_-" for c in name) and name.isascii()


def _toml_header(name: str) -> str:
    if _is_bare_key(name):
        return f"[{name}]"
    return f'["{_toml_escape(name)}"]'


def _dump_toml(mapping: dict[str, dict]) -> str:
    lines: list[str] = []
    for name in sorted(mapping):
        entry = mapping[name]
        lines.append(_toml_header(name))
        lines.append(f'type = "{entry["type"]}"')
        lines.append(f'stable_url = "{_toml_escape(entry["stable_url"])}"')
        lines.append(f'stable_regex = "{_toml_escape(entry["stable_regex"])}"')
        if "unstable_url" in entry:
            lines.append(f'unstable_url = "{_toml_escape(entry["unstable_url"])}"')
            lines.append(f'unstable_regex = "{_toml_escape(entry["unstable_regex"])}"')
        tags = ", ".join(f'"{_toml_escape(t)}"' for t in entry["tags"])
        lines.append(f"tags = [{tags}]")
        flavors = ", ".join(f'"{f}"' for f in entry["flavors"])
        lines.append(f"flavors = [{flavors}]")
        fixups = entry.get("version_fixups", [])
        if fixups:
            rendered = ", ".join(f'"{_toml_escape(f)}"' for f in fixups)
            lines.append(f"version_fixups = [{rendered}]")
        lines.append("")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Convert legacy ubuntu-desktop-versions package metadata to TOML."
    )
    parser.add_argument("legacy_path", help="path to ubuntu-desktop-versions/packages.py")
    parser.add_argument("out_path", help="path to write packages.toml")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    mapping = convert(args.legacy_path)
    with open(args.out_path, "w", encoding="utf-8") as handle:
        handle.write(_dump_toml(mapping))
    print(f"Wrote {len(mapping)} packages to {args.out_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
