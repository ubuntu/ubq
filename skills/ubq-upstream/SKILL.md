---
name: ubq-upstream
description: "Use when querying third-party upstream data through the ubq library's 'upstream' provider: get the latest upstream release version of a package and resolve its upstream project location. Covers the static data-file model (packages.toml), the source types (gnome/gitlab/sourceforge/gnu/kde/gstreamer/pypi/cpan/http/ftp), why series/pocket/archive are ignored, no-auth access, and the fact that bugs and merge requests are NOT supported. Load the central 'ubq' skill for the shared API and models."
version: 1.0.0
author: Lena Voytek
metadata:
    tags: [ubq, upstream, ubuntu, versions, packages, releases, data-file, third-party]
    related_skills: [ubq, ubq-launchpad, ubq-github, ubq-snapcraft]
---

# ubq — Upstream Provider (`provider_name="upstream"`)

## Overview

The Upstream provider serves **third-party upstream** metadata for packages —
the version a project ships *at its own release site*, independent of any
Ubuntu/Debian archive. It answers "what's the latest upstream release of this
package, and where does that project live?" It is **read-only** and supports
just two capabilities: **version** and **package**. It has **no** bug or
merge-request capability — calling those raises `ValueError`.

Read the central **`ubq`** skill first for the `QueryService` API, auth modes,
and model shapes. This skill covers Upstream-specific arguments, the data-file
model, and field semantics.

Capabilities: version ✅ · package ✅ · bug ❌ · merge_request ❌
(the same capability shape as Snapcraft).

Unlike the other providers, upstream does **not** call a live service API for
its package list. It is driven by a generated static data file shipped inside
the library (`src/ubq/providers/upstream/data/packages.toml`). Each entry names
a package, a source *type*, a download/listing URL, and a regex for extracting
the version. Package resolution is offline (pure data-file lookup); version
resolution fetches that one URL over HTTP/FTP and scrapes the highest version.

**Scope.** The data file deliberately excludes sources that other tools/
providers already cover: it does **not** track GitHub- or Launchpad-hosted
projects, nor sources followed via the Debian or Ubuntu archives. If a package
isn't in the file (or was classified out of scope), every call returns `None`.
For a deb package's *archive* version use `ubq-launchpad`; for a snap use
`ubq-snapcraft`; for a GitHub project's issues/PRs use `ubq-github`.

## When to Use

- Find the latest **upstream release version** of a package as published at its
  own project site (GNOME download server, a GitLab tags page, SourceForge,
  GNU, KDE, GStreamer, PyPI, CPAN, or a plain HTTP/FTP directory listing).
- Resolve a package's **upstream project location** (its project page or the
  stable download URL).
- Diff "what upstream shipped" against "what Ubuntu/Debian shipped" — pair an
  upstream `get_version` with a Launchpad `get_version` (see example below).

Don't use for: archive/distribution versions (use `ubq-launchpad`), snap
channel versions (use `ubq-snapcraft`), GitHub/Launchpad-hosted sources (not in
scope — the data file omits them), or bugs / merge-pull requests (Upstream
supports neither).

## Authentication

The upstream provider needs **no credentials** — anonymous is the only mode.
`login()` builds a trivial session (no token, no keyring, no network), so it is
completely safe for servers, CI, containers, and automated agents.

```python
from ubq import QueryService

service = QueryService()
service.login(provider_name="upstream")          # no credentials, ever
```

Passing `ProviderCredentials` is accepted for interface uniformity but is
ignored — there is nothing to authenticate against. Don't supply a token; there
is no private upstream data and no rate-limited authenticated tier here.

## The Data-File Model (packages.toml)

The provider is backed by `src/ubq/providers/upstream/data/packages.toml`, a
generated table with one section per package:

```toml
[accountsservice]
type = "gitlab"
stable_url = "https://gitlab.freedesktop.org/accountsservice/accountsservice/tags"
stable_regex = "tags/(?:accountsservice[-_])?v?([0-9][0-9.]*)"
tags = []
flavors = ["ubuntu"]
version_fixups = ["underscore_to_dot_if_full", "dash_to_dot_if_full"]
```

Fields (see `data_file.py` / `UpstreamSource`):

- **`type`** — source classification. Must be one of the ten valid types:
  `gnome`, `gitlab`, `sourceforge`, `gnu`, `kde`, `gstreamer`, `pypi`, `cpan`,
  `http`, `ftp`. (All ten currently share one `DirectoryHandler`; the distinct
  types are kept for provenance and future divergence.)
- **`stable_url`** (required) — the listing/page/directory URL to fetch. Its
  final path segment may itself be a version *regex* (e.g.
  `.../files/aa-lib/([0-9.]+)`); the handler then descends into the
  highest-versioned matching subdirectory before scraping.
- **`stable_regex`** (required) — regex whose **group 1** is the version, run
  against every line of the fetched body; the dpkg-highest match wins.
- **`version_fixups`** — ordered rewrite ops applied to each raw match (e.g.
  `underscore_to_dot_if_full`, `dash_to_dot_if_full`, `gnome_prerelease`,
  `sub:PATTERN=>REPL`, `prepend:X`, `append:X`, `drop_if_equal:X`,
  `libreoffice_triplet`, `mozjs_dots`, `first_two_dotted`). These normalize
  upstream's formatting toward a Debian-comparable version.
- **`unstable_url` / `unstable_regex`** — optional development-series variants.
  **Not used by the current `get_version` path** (which always reads the stable
  pair); present in the data model only.
- **`project_url`** — optional canonical project page; used by `get_package`.
- **`tags` / `flavors`** — provenance metadata (e.g. `flavors=["kubuntu"]`);
  not part of the returned records.

`load_sources()` validates every entry at load time: an unknown/out-of-scope
`type`, a missing `stable_url`/`stable_regex`, or an un-compilable regex raises
`ValueError`. The package list is loaded lazily on first query and cached on the
provider instance.

## Versions

`get_version(package_name, archive, series, pocket, provider_name)` returns the
**latest upstream release** found at the package's stable source.

```python
service.login(provider_name="upstream")
v = service.get_version(
    package_name="accountsservice",
    archive="",            # ignored — pass "" (see note)
    series="",             # ignored — echoed back verbatim
    pocket=None,           # ignored — echoed back verbatim
    provider_name="upstream",
)
if v:
    print(v.package_name, v.version_string)   # e.g. accountsservice 26.27.3
```

Behavior and gotchas:

- **`series` and `pocket` are ignored** — upstream sources have no notion of an
  Ubuntu series or pocket. They are accepted for the shared `QueryService`
  signature and **echoed straight back** onto the returned `VersionRecord`
  (whatever you pass in `series`/`pocket` reappears there unchanged).
- **`archive` is also ignored** for lookup and merely stored on the record.
  There is no distribution/base concept here, so `archive=""` is the idiomatic
  value (the bundled comparison script passes `""`). Don't pass `"ubuntu"` /
  `"debian"` expecting it to mean anything.
- The result carries **only the version**: `version_string` is populated;
  `changelog`, `created_at`, and `released_at` are **always `None`** for
  upstream (the provider sets `changelog=None` and never fills the dates).
- **Fetch mechanics:** the handler resolves any trailing version-regex path
  segment (descending to the newest matching subdir), fetches the URL over
  HTTP/FTP (`User-Agent: ubq/1.0`), applies `version_fixups` to each match, and
  returns the dpkg-highest version (a pure-Python dpkg comparator, no
  `python-apt`).
- **Returns `None`** if the package isn't in the data file *or* if the fetch
  yielded no matching version. A network failure that isn't a timeout (DNS,
  connection refused, HTTP error) is swallowed and also surfaces as `None` — so
  a `None` from `get_version` can mean either "unknown package" or "couldn't
  reach/parse the source right now". Distinguish them with `get_package`
  (offline): if `get_package` returns a record but `get_version` returns `None`,
  the package is known and the fetch/scrape came up empty.
- A genuine **timeout** raises `ubq.RequestTimeoutError` (default 30s), not
  `None`. Raise `QueryService(timeout=...)` for slow mirrors.

Diff upstream vs. the Ubuntu archive (pair with the Launchpad provider):

```python
from ubq import QueryService

service = QueryService()
service.login(provider_name="upstream")
service.login(provider_name="launchpad")          # anonymous read

upstream = service.get_version("accountsservice", archive="", series="",
                               pocket=None, provider_name="upstream")
archived = service.get_version("accountsservice", archive="ubuntu",
                               series="resolute", pocket="Release",
                               provider_name="launchpad")
print("upstream:", upstream.version_string if upstream else "n/a")
print("ubuntu:  ", archived.version_string if archived else "n/a")
```

## Packages

`get_package(package_name, archive, provider_name)` resolves a package's
upstream project location. This is a **pure data-file lookup — no network**.

```python
pkg = service.get_package(package_name="accountsservice", archive="",
                          provider_name="upstream")
print(pkg.name, pkg.package_url)
```

- `package_url` is the source's **`project_url` if present, otherwise its
  `stable_url`**. Because the fallback is `stable_url`, the URL may be a raw
  download/listing target and can even contain a trailing version-regex segment
  (e.g. `.../files/aa-lib/([0-9.]+)`) — it is **not** guaranteed to be a
  clean, browsable project home. Treat `package_url` as "where this version
  came from," not necessarily a landing page.
- `archive` is ignored for lookup and only echoed onto the record; pass `""`.
- Returns `None` if the package isn't in the data file.

## Example Programs (source repo `scripts/`)

The ubq source repository ships upstream-related scripts. They're references,
not a runtime dependency — your code calls the library directly.

- `check_upstream_versions_table.py` — the canonical end-to-end usage: logs in
  to `upstream`, iterates a package table, and calls
  `service.get_version(package_name=..., archive="", series="", pocket=None,
  provider_name="upstream")` for each. Copy its call shape.
  Flags: `[--url URL] [--package PKG ...] [--limit N] [--verbose]`.
- `convert_upstream_packages.py` — the **generator** that builds
  `data/packages.toml` from the legacy `ubuntu-desktop-versions` package map
  (classifies each source by URL host, drops out-of-scope
  github/launchpad/debian/ubuntu entries, emits typed TOML). Run this to
  regenerate/refresh the data file; it is not part of normal querying.

## Common Pitfalls

1. **Passing `series`/`pocket`/`archive` and expecting them to filter.** All
   three are ignored by the upstream provider. `series`/`pocket` are echoed
   back onto the record; `archive` is stored only. Pass `series=""`,
   `pocket=None`, `archive=""`.
2. **Reading `None` as "no such package".** `get_version` also returns `None`
   on a non-timeout fetch/parse failure. Use `get_package` (offline) to confirm
   whether the package is actually in the data file before concluding it's
   unknown.
3. **Expecting a changelog or dates.** Upstream `VersionRecord`s carry only
   `version_string`; `changelog`, `created_at`, and `released_at` are always
   `None`.
4. **Assuming `package_url` is a tidy project homepage.** It's `project_url`
   when set, else the raw `stable_url` (which may include a version-regex path
   segment). Don't render it blindly as a canonical link.
5. **Calling unsupported capabilities.** `get_bug`/`search_bugs`/`submit_bug`
   and the merge-request methods raise `ValueError: Provider 'upstream' does not
   support ... queries.` Branch on `supports("upstream", ...)` first.
6. **Looking for a GitHub/Launchpad-hosted package here.** Out of scope by
   design — the data file omits them. Use `ubq-github` / `ubq-launchpad`.
7. **Trying to authenticate.** There are no upstream credentials; supplying a
   token does nothing. Just `login(provider_name="upstream")`.
8. **Slow/unreachable mirror.** A live version fetch can hit a slow SourceForge/
   FTP mirror and raise `ubq.RequestTimeoutError` (default 30s). Raise
   `QueryService(timeout=...)` when scanning many packages.

## Verification Checklist

- [ ] `login(provider_name="upstream")` (no credentials needed or used)
- [ ] `get_version` called with `archive=""`, `series=""`, `pocket=None`
- [ ] Only `get_version` / `get_package` used (no bug/MR calls)
- [ ] `None` handled — and disambiguated via `get_package` (unknown pkg vs. fetch miss)
- [ ] No reliance on `changelog` / `created_at` / `released_at` (always `None`)
- [ ] `package_url` treated as source location, not guaranteed project homepage
- [ ] `RequestTimeoutError` handled / `timeout` raised for slow-mirror scans
