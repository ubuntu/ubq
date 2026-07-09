---
name: ubq-snapcraft
description: "Use when querying snap data through the ubq library's 'snapcraft' provider: fetch a snap's version on a given channel (track/risk) and resolve a snap package's store page. Covers the channel model (series=track, pocket=risk), the snapcraft.io archive argument, optional macaroon auth, and the fact that bugs and merge requests are NOT supported. Load the central 'ubq' skill for the shared API and models."
version: 1.0.0
author: Lena Voytek
metadata:
    tags: [ubq, snapcraft, snap, versions, packages, channels, store]
    related_skills: [ubq, ubq-launchpad, ubq-github, ubq-upstream]
---

# ubq — Snapcraft Provider (`provider_name="snapcraft"`)

## Overview

The Snapcraft provider reads snap data from the Snapcraft Store API
(`https://api.snapcraft.io/v2`). It is **read-only** and supports just two
capabilities: **version** and **package**. It has **no** bug or merge-request
capability — calling those raises `ValueError`.

Read the central **`ubq`** skill first for the `QueryService` API, auth modes,
and model shapes. This skill covers Snapcraft-specific arguments and the channel
model.

Capabilities: version ✅ · package ✅ · bug ❌ · merge_request ❌.

## When to Use

- Look up the version a snap currently exposes on a specific channel
  (e.g. `latest/stable`).
- Resolve a snap's store page / metadata.

Don't use for: bugs or merge/pull requests (Snapcraft supports neither — use
`ubq-launchpad` or `ubq-github`), or deb package versions (use `ubq-launchpad`).

## Authentication

Public snap version/package data needs **no authentication** — anonymous is the
normal mode.

```python
from ubq import QueryService

service = QueryService()
service.login(provider_name="snapcraft")          # anonymous; fine for public data
```

If you do need auth, the token is a **store macaroon** string. With no explicit
credentials the provider falls back to the `SNAPCRAFT_STORE_AUTH` environment
variable. The macaroon is sent as `Authorization: Macaroon <token>` (the
provider adds the `Macaroon ` prefix if you omit it).

```python
from ubq.models import ProviderCredentials
service.login(provider_name="snapcraft",
              credentials=ProviderCredentials(token=macaroon))
```

Token from a file — use `ProviderCredentials.from_file(path)` (reads + strips it;
raises `FileNotFoundError`/`ValueError` on missing/empty). Never log or commit a
macaroon.

## The Channel Model (series = track, pocket = risk)

A snap channel is `<track>/<risk>`, e.g. `latest/stable`, `1.0/beta`. ubq maps
this onto its generic version arguments:

- **`series`** = the channel **track** (e.g. `latest`, `1.0`).
- **`pocket`** = the channel **risk** (e.g. `stable`, `candidate`, `beta`,
  `edge`).
- **`archive`** = the Snapcraft base URL, conventionally `"https://snapcraft.io/"`
  (stored on the returned record and used to build a fallback package URL).

Two matching modes:

- If `pocket` is provided → match the channel-map entry where
  `channel.track == series` **and** `channel.risk == pocket`.
- If `pocket is None` → match where `channel.name == series` (so you can pass a
  full channel name like `"latest/stable"` as `series` with `pocket=None`).

Splitting a `track/risk` string the way the example script does:

```python
parts = channel.split("/", 1)
if len(parts) == 2:
    series, pocket = parts            # "latest", "stable"
else:
    series, pocket = channel, None    # whole string as track, no risk
```

Unlike Launchpad, Snapcraft does **not** validate the pocket against a fixed
set — an unknown track/risk simply yields no match (`None`).

## Versions

```python
service.login(provider_name="snapcraft")
v = service.get_version(
    package_name="firefox",
    archive="https://snapcraft.io/",   # snapcraft base URL
    series="latest",                   # track
    pocket="stable",                   # risk
    provider_name="snapcraft",
)
if v:
    label = f"{v.series}/{v.pocket}" if v.pocket else v.series
    print(v.package_name, label, v.version_string)
```

- Queries `GET /snaps/info/{name}?fields=name,version,channel-map` and scans the
  channel map for the first matching entry.
- `VersionRecord.released_at` is the channel's `released-at` (UTC) when present;
  `changelog` and `created_at` are not populated for snaps.
- Returns `None` if the snap or the requested channel isn't found.

## Packages

```python
pkg = service.get_package(
    package_name="firefox",
    archive="https://snapcraft.io/",
    provider_name="snapcraft",
)
print(pkg.name, pkg.package_url)
```

- Queries `GET /snaps/info/{name}?fields=name,store-url`.
- `package_url` is the snap's `store-url` when available, otherwise
  `"{archive}/{name}"` (e.g. `https://snapcraft.io/firefox`).
- Returns `None` if the snap name has no `name` in the response.

## Integration Example

```python
from ubq import QueryService

service = QueryService()           # construct once, reuse
service.login(provider_name="snapcraft")   # anonymous; public data needs no auth

def snap_version(name: str, channel: str) -> str | None:
    """channel is '<track>/<risk>', e.g. 'latest/stable'."""
    track, _, risk = channel.partition("/")
    v = service.get_version(
        package_name=name,
        archive="https://snapcraft.io/",
        series=track,
        pocket=risk or None,
        provider_name="snapcraft",
    )
    return v.version_string if v else None

print(snap_version("firefox", "latest/stable"))
```

The source repository's `scripts/get_snap_version.py` is a runnable version of
this same call if you have a checkout; it is an example, not a runtime
dependency.

## Common Pitfalls

1. **Treating `archive` like a distro.** For Snapcraft, `archive` is the
   snapcraft.io base URL (`"https://snapcraft.io/"`), not `"ubuntu"`/`"debian"`.
2. **Swapping track and risk.** `series` is the **track** (`latest`, `1.0`);
   `pocket` is the **risk** (`stable`, `beta`, …). Reversing them yields `None`.
3. **Calling unsupported capabilities.** `get_bug`/`search_bugs`/`submit_bug` and
   the merge-request methods raise
   `ValueError: Provider 'snapcraft' does not support ... queries.`
4. **Expecting a changelog.** Snap `VersionRecord`s have no changelog and no
   `created_at`; only `released_at` is populated (when the store provides it).
5. **Over-authenticating.** Public data needs no macaroon; only supply one for
   restricted access. If you do, keep it out of logs and commits.
6. **Passing a full channel as `series` with a non-None `pocket`.** Either split
   into track+risk, or pass the whole `track/risk` as `series` with
   `pocket=None` — not a mix.

## Verification Checklist

- [ ] `login(provider_name="snapcraft")` (anonymous is fine for public data)
- [ ] `archive="https://snapcraft.io/"`
- [ ] `series` = track, `pocket` = risk (or full channel in `series` with `pocket=None`)
- [ ] Only `get_version` / `get_package` used (no bug/MR calls)
- [ ] `None` results (snap or channel not found) handled
- [ ] Any macaroon sourced from env/file/secret, never logged or committed
