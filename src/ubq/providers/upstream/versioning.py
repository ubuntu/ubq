# src/ubq/providers/upstream/versioning.py
"""Pure-Python Debian-style version comparison and version fixups.

This ports dpkg's version comparison algorithm (normally provided by
``apt_pkg.version_compare``) so the upstream provider has no dependency on
``python-apt``. Only the upstream-version portion matters here, so the epoch
and Debian-revision handling is intentionally minimal: a leading ``epoch:`` is
stripped and the remainder is compared as a single dpkg version string.
"""

import re

_TILDE_WEIGHT = -1


def _strip_epoch(version: str) -> str:
    """Drop a leading ``N:`` epoch prefix if present."""
    head, sep, tail = version.partition(":")
    return tail if sep and head.isdigit() else version


def _order(char: str) -> int:
    """Return the dpkg sort weight of a single non-digit character.

    ``~`` sorts before everything (including the empty string / end of part),
    letters sort in ASCII order, and all other characters sort after letters.
    The end-of-part position is treated by the caller as weight 0.
    """
    if char == "~":
        return _TILDE_WEIGHT
    if char.isalpha():
        return ord(char)
    return ord(char) + 256


def _compare_part(a: str, b: str) -> int:
    """Compare two dpkg version strings (alternating non-digit / digit runs)."""
    ia = ib = 0
    la, lb = len(a), len(b)
    while ia < la or ib < lb:
        # Compare the non-digit run by dpkg character weight.
        while (ia < la and not a[ia].isdigit()) or (ib < lb and not b[ib].isdigit()):
            wa = _order(a[ia]) if ia < la and not a[ia].isdigit() else 0
            wb = _order(b[ib]) if ib < lb and not b[ib].isdigit() else 0
            if wa != wb:
                return wa - wb
            if ia < la and not a[ia].isdigit():
                ia += 1
            if ib < lb and not b[ib].isdigit():
                ib += 1
        # Compare the digit run numerically (leading zeros ignored).
        na = nb = 0
        while ia < la and a[ia].isdigit():
            na = na * 10 + int(a[ia])
            ia += 1
        while ib < lb and b[ib].isdigit():
            nb = nb * 10 + int(b[ib])
            ib += 1
        if na != nb:
            return na - nb
    return 0


def compare_versions(a: str | None, b: str | None) -> int:
    """Compare two upstream version strings dpkg-style.

    ``None`` and ``""`` sort lower than any real version. Returns a negative,
    zero, or positive integer when ``a`` is less than, equal to, or greater
    than ``b``.
    """
    if a is None or a == "":
        return 0 if (b is None or b == "") else -1
    if b is None or b == "":
        return 1
    return _compare_part(_strip_epoch(a), _strip_epoch(b))


def max_version(a: str | None, b: str | None) -> str | None:
    """Return whichever of ``a``/``b`` is greater per :func:`compare_versions`."""
    return a if compare_versions(a, b) > 0 else b


_UNDERSCORED_VERSION = re.compile(r"[0-9][0-9A-Za-z_-]+")
_DASHED_VERSION = re.compile(r"[0-9][0-9-]+")
_GNOME_NEW_VERSION = re.compile(r"(([0-9]+(?:\.[0-9]+)?)(?:\.(alpha|beta|rc|[0-9]+))?)")


def _libreoffice_triplet(v: str) -> str:
    """Reduce a 4-part version to a triplet, tilde-prefixing any pre-release."""
    v = v[0:5] + v[7:]
    if len(v) > 5 and v[5] == ".":
        v = v[0:5] + "~" + v[6:]
    return v


def _mozjs_dots(v: str) -> str:
    """Insert dots after the first two digits (``128`` -> ``1.2.8``)."""
    if len(v) >= 3:
        return v[0] + "." + v[1] + "." + v[2:]
    return v


def _first_two_dotted(v: str) -> str:
    """Dot-separate the first two characters (``30`` -> ``3.0``)."""
    if len(v) >= 2:
        return v[0] + "." + v[1]
    return v


def _underscore_to_dot_if_full(v: str) -> str:
    """Replace ``_`` with ``.`` when the whole string is an underscored version."""
    if _UNDERSCORED_VERSION.fullmatch(v):
        return v.replace("_", ".")
    return v


def _dash_to_dot_if_full(v: str) -> str:
    """Replace ``-`` with ``.`` when the whole string is a dashed version."""
    if _DASHED_VERSION.fullmatch(v):
        return v.replace("-", ".")
    return v


def _gnome_prerelease(v: str) -> str:
    """Tilde-separate a non-numeric GNOME pre-release token (``50.alpha``)."""
    match = _GNOME_NEW_VERSION.fullmatch(v)
    if match:
        pre_release = match.group(3)
        if pre_release and not pre_release.isnumeric():
            return f"{match.group(2)}~{pre_release}"
    return v


def apply_fixups(version: str, fixups: list[str]) -> str | None:
    """Apply ordered named fixup operations to a version string.

    Each entry is ``"OP"`` or ``"OP:ARG"``. Returns the rewritten version, or
    ``None`` if a ``drop_if_equal`` op matched (the version should be dropped).
    Unknown ops raise :class:`ValueError`.
    """
    result = version
    for fixup in fixups:
        op, _, arg = fixup.partition(":")
        if op == "sub":
            pattern, _, replacement = arg.partition("=>")
            result = re.sub(pattern, replacement, result)
        elif op == "prepend":
            result = arg + result
        elif op == "append":
            result = result + arg
        elif op == "drop_if_equal":
            if result == arg:
                return None
        elif op == "libreoffice_triplet":
            result = _libreoffice_triplet(result)
        elif op == "mozjs_dots":
            result = _mozjs_dots(result)
        elif op == "first_two_dotted":
            result = _first_two_dotted(result)
        elif op == "underscore_to_dot_if_full":
            result = _underscore_to_dot_if_full(result)
        elif op == "dash_to_dot_if_full":
            result = _dash_to_dot_if_full(result)
        elif op == "gnome_prerelease":
            result = _gnome_prerelease(result)
        else:
            raise ValueError(f"Unknown version fixup operation: {fixup!r}")
    return result
