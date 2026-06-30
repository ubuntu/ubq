---
name: ubq
description: "Use when an agent must query Ubuntu data (bugs, package versions, packages, merge/pull requests) from Launchpad, GitHub, or Snapcraft via the ubq Python library. Central hub: architecture, the QueryService API, authentication (anonymous / token / token-from-file), the provider capability matrix, and shared data models. Load a provider sub-skill (ubq-launchpad, ubq-github, ubq-snapcraft) for per-service identifiers and field semantics."
version: 1.0.0
author: Lena Voytek
metadata:
    tags: [ubq, ubuntu, launchpad, github, snapcraft, bugs, packages, data-query, python]
    related_skills: [ubq-launchpad, ubq-github, ubq-snapcraft]
---

# ubq — Ubuntu Query Library

## Overview

`ubq` (Ubuntu Query) is a Python library that gives one common interface for
reading (and, for some providers, writing) Ubuntu-related data spread across
several services. Instead of learning the Launchpad API, the GitHub GraphQL/REST
API, and the Snapcraft Store API separately, an agent talks to a single
`QueryService` and gets back normalized dataclass records.

Two layers (see `src/ubq/README.md`):

- **models** (`src/ubq/models/`) — frozen dataclasses describing the data:
  `BugRecord`, `VersionRecord`, `PackageRecord`, `MergeRequestRecord`, plus
  supporting records. Every provider returns these same types.
- **providers** (`src/ubq/providers/`) — adapters that fetch from an external
  service and convert its responses into model records. A `ProviderRegistry`
  manages provider sessions.

The top-level `ubq` package exposes **`QueryService`** as the single entry point.
This is the API agents should call — not the provider classes directly, and not
the `ubuntu-mcp` wrapper (whose method signatures differ from ubq's).

Three providers ship today:

| provider name | service           | reads                          | writes |
|---------------|-------------------|--------------------------------|--------|
| `launchpad`   | Launchpad         | bugs, versions, packages, MRs  | bugs   |
| `github`      | GitHub            | issues (bugs), pull requests   | issues |
| `snapcraft`   | Snapcraft Store   | snap versions, snap packages   | —      |

Confirm at runtime with `QueryService().available_providers()` →
`('github', 'launchpad', 'snapcraft')`.

## When to Use

- Programmatically fetching an Ubuntu/Debian package version across series, a
  Launchpad bug, a GitHub issue/PR, or a snap's channel version.
- Searching or submitting Launchpad bugs / GitHub issues from a script or agent.
- Any task where you'd otherwise hand-roll a Launchpad/GitHub/Snapcraft API call
  for data ubq already models.

Don't use for: tasks the providers don't cover (e.g. Snapcraft has no bug or
merge-request capability; GitHub has no package/version capability). Calling an
unsupported capability raises `ValueError`. See the capability matrix below.

## Installation & Integration

`ubq` is published on PyPI and requires **Python ≥ 3.13**. Add it to a project
with whatever package manager the project uses:

```bash
pip install ubq          # pip
uv add ubq               # uv-managed project
poetry add ubq           # poetry
# or add "ubq>=0.5" to your [project].dependencies / requirements.txt
```

Then import and use it from your own code:

```python
from ubq import QueryService, RequestTimeoutError
from ubq.models import (
    ProviderCredentials, BugSearchRecord, BugSubmissionRecord, UserRecord,
)

service = QueryService()
print(service.available_providers())     # ('github', 'launchpad', 'snapcraft')
```

Public names: `QueryService` and `RequestTimeoutError` come from the top-level
`ubq` package; all record/dataclass types come from `ubq.models`. There is no
`__version__` attribute — check the installed version with your package manager
(`pip show ubq`) if needed.

The integration pattern is always: construct one `QueryService`, `login()` each
provider you need, then call query methods, passing `provider_name` each time.
A single service instance can hold sessions for several providers at once, so
construct it once (e.g. at app/module startup) and reuse it.

The source repository also ships runnable example programs under `scripts/`
(one per major operation). If you have a source checkout they're the quickest
way to see a full call in context; they are examples, not a required runtime.

## The QueryService API

`QueryService(registry=None, timeout=30)`. Default `timeout` is 30s per request;
on timeout a `ubq.RequestTimeoutError` is raised.

**Always `login()` first**, then call query methods. Each call passes
`provider_name` so one service instance can talk to several providers.

```python
from ubq import QueryService
from ubq.models import ProviderCredentials

service = QueryService()
service.login(provider_name="launchpad")          # anonymous; see Authentication
bug = service.get_bug(bug_id="1993329", provider_name="launchpad")
```

Method reference (exact signatures — note positional/keyword shapes):

| method | signature | returns |
|--------|-----------|---------|
| `login` | `login(provider_name, credentials=None, force=False)` | `None` |
| `get_bug` | `get_bug(bug_id, provider_name, metadata_only=False)` | `BugRecord \| None` |
| `search_bugs` | `search_bugs(query, provider_name)` | `list[BugRecord]` |
| `submit_bug` | `submit_bug(submission, provider_name)` | `BugRecord \| None` |
| `get_version` | `get_version(package_name, archive, series, pocket, provider_name)` | `VersionRecord \| None` |
| `get_package` | `get_package(package_name, archive, provider_name)` | `PackageRecord \| None` |
| `get_merge_request` | `get_merge_request(author, project, branch, merge_request_id, provider_name)` | `MergeRequestRecord \| None` |
| `get_merge_requests_from_user` | `get_merge_requests_from_user(user_id, provider_name)` | `list[MergeRequestRecord]` |
| `available_providers` | `available_providers()` | `tuple[str, ...]` |
| `capabilities` | `capabilities(provider_name)` | `frozenset[str]` |
| `supports` | `supports(provider_name, capability)` | `bool` |

Key gotchas:

- `get_version` and `get_package` take an **`archive`** argument
  (`"ubuntu"`, `"debian"`, or the Snapcraft base URL). This is required and
  provider-specific — see the sub-skills.
- `get_merge_request` is keyed by **four** parts
  (`author`, `project`, `branch`, `merge_request_id`), not a single ID string.
  Providers interpret these differently (GitHub ignores `branch`).
- `metadata_only=True` on `get_bug` skips the extra requests for comments and
  tasks — much faster when you only need title/tags/dates.
- A `None` return means "not found" (e.g. 404). An empty `list` means "no
  matches". Neither is an error.

## Authentication

`login()` builds a session and caches it (keyed by lowercased provider name).
Subsequent `login()` calls for the same provider reuse the cached session unless
you pass `force=True`. Authenticate **each provider you intend to use**.

There are three credential modes. The mode is the same call shape for every
provider; only the meaning of the token differs.

### 1. Anonymous (no credentials)

```python
service.login(provider_name="launchpad")        # credentials defaults to None
```

What "anonymous" does per provider (important — it's not identical):

- **launchpad** — calls `Launchpad.login_anonymously("ubq",
  service_root="production", ...)`. A genuine credential-free, read-only session:
  no keyring access, no browser, no interactive authorization. Safe for servers,
  CI, containers, and automated agents. Reads public bugs/packages/versions;
  cannot submit bugs.
- **github** — falls back to a token from the `GITHUB_TOKEN` env var, then from
  `gh auth token` (the GitHub CLI). If neither exists, requests go out
  **unauthenticated** and hit GitHub's low anonymous rate limit. So "anonymous"
  GitHub silently uses ambient credentials if present.
- **snapcraft** — falls back to the `SNAPCRAFT_STORE_AUTH` env var. Public snap
  version/package data needs no auth at all, so anonymous is normal here.

### 2. Explicit token

```python
service.login(
    provider_name="github",
    credentials=ProviderCredentials(token="ghp_..."),
)
```

Token meaning per provider:

- **launchpad** — a launchpadlib **OAuth credentials string** (the multi-line
  `[1]\nconsumer_key=...` blob produced by launchpadlib). Parsed with
  `Credentials.from_string(token)`. Required to submit bugs or read private data.
- **github** — a Personal Access Token / `ghp_...`, sent as `Bearer`.
- **snapcraft** — a store **macaroon** string (with or without the leading
  `Macaroon ` prefix).

### 3. Token loaded from a file

Use `ProviderCredentials.from_file(path)` — it reads the file, strips surrounding
whitespace (trailing newlines are common in OAuth credential files), and returns
ready-to-use credentials. It raises `FileNotFoundError` if the path is missing
and `ValueError` if the file is empty.

```python
from ubq.models import ProviderCredentials

credentials = ProviderCredentials.from_file(cred_file) if cred_file else None
service.login(provider_name="launchpad", credentials=credentials)
```

`from_file` also accepts an optional `username=` keyword. Never echo, log, or
commit the token; treat a credentials file as sensitive and reference it by path
only. For Launchpad, an invalid/corrupt OAuth blob still surfaces from
launchpadlib as `lazr.restfulclient.errors.CredentialsFileError` at login —
catch it and surface a clean message, not the raw token.

### Re-authentication

```python
service.login(provider_name="launchpad", credentials=creds, force=True)
```

`force=True` discards the cached session and re-authenticates (e.g. switching
from anonymous to a token).

## Provider Capability Matrix

Not every provider implements every capability. Calling a method the provider
can't serve raises `ValueError: Provider 'X' does not support Y queries.`

| capability (method) | launchpad | github | snapcraft |
|---------------------|:---------:|:------:|:---------:|
| `get_bug` / `search_bugs` / `submit_bug` | ✅ | ✅ (issues) | ❌ |
| `get_version` | ✅ | ❌ | ✅ |
| `get_package` | ✅ | ❌ | ✅ |
| `get_merge_request` / `get_merge_requests_from_user` | ✅ | ✅ (PRs) | ❌ |

Branch **before** calling rather than catching the `ValueError`, using runtime
introspection (works without `login()`):

```python
service.capabilities("snapcraft")        # frozenset({'version', 'package'})
service.supports("snapcraft", "bug")     # False  -> skip bug queries
service.supports("launchpad", "bug")     # True
```

Capability names are `"bug"`, `"version"`, `"package"`, `"merge_request"`.
`capabilities()`/`supports()` raise `ValueError` for an unknown provider; an
unrecognized capability name just returns `False`.

Identifier formats and field semantics differ sharply between providers (a
GitHub bug id is `owner/repo#number`; a Launchpad bug id is a bare number; a
Launchpad MR needs `~author/project/branch/+merge/id`). **Load the matching
sub-skill before constructing identifiers:** `ubq-launchpad`, `ubq-github`,
`ubq-snapcraft`.

## Data Models (what you get back)

All models are frozen dataclasses in `ubq.models`. Optional fields default to
`None` or empty list. Datetimes are `datetime | None`. Common shapes:

- **`BugRecord`**: `provider_name, id, title, description, tags[],
  comments[CommentRecord], created_at, updated_at, last_message_at,
  last_patch_at, owner[UserRecord], assignee[UserRecord], bug_tasks[BugTaskRecord]`.
  With `metadata_only=True`, `comments`/`bug_tasks` are empty.
- **`BugTaskRecord`**: per-package task on a bug — `title, target, package_name,
  importance, status, milestone, owner, assignee`, plus a full set of lifecycle
  `date_*` fields (`date_created`, `date_confirmed`, `date_fix_released`, …).
- **`BugSearchRecord`** (input to `search_bugs`): `provider_name, title, tags[],
  created_before, created_since, modified_since, owner[UserRecord],
  assignee[UserRecord], milestone, status, importance`.
- **`BugSubmissionRecord`** (input to `submit_bug`): `provider_name, title,
  package_names[], description, importance, status, tags[],
  subscribers[UserRecord], assignee[UserRecord], private, milestone`.
- **`VersionRecord`**: `provider_name, version_string, package_name, archive,
  series, pocket, created_at, released_at, changelog`.
- **`PackageRecord`**: `provider_name, name, archive, package_url`.
- **`MergeRequestRecord`**: `provider_name, id, title, description, status,
  source_branch, target_branch, web_url, author[UserRecord],
  assignees[UserRecord], created_at, updated_at, merged_at, package, added_lines,
  removed_lines, votes[MergeRequestVoteRecord]`.
- **`MergeRequestVoteRecord`**: `voter[UserRecord], vote_value(int),
  vote(str), message, voted_at, unvoted_at`. `vote_value` is +1 approve,
  -1 changes-requested/disapprove, 0 neutral.
- **`UserRecord`**: `username, display_name, profile_url`.
- **`CommentRecord`**: `author[UserRecord], content, created_at, edited_at`.
- **`ProviderCredentials`**: `username, token` (only `token` is used by current
  providers).

Because records are frozen, treat them as read-only; build new ones rather than
mutating.

## Errors to Handle

- **`ubq.RequestTimeoutError`** — a request exceeded `timeout` seconds. Carries
  `.provider_name` and `.timeout`. `from ubq import RequestTimeoutError`.
- **`ValueError`** — unknown provider, unsupported capability, missing session
  (`"No active session for provider 'X'. Call login() first."`), or an invalid
  identifier / pocket / bug status / importance.
- **`lazr.restfulclient.errors.CredentialsFileError`** — malformed Launchpad
  token string (raised during `login`).
- **`RuntimeError`** — GitHub GraphQL returned errors.

## End-to-End Example

```python
from ubq import QueryService

service = QueryService()
service.login(provider_name="launchpad")        # anonymous read

# Compare Ubuntu vs Debian versions of a package
ubuntu = service.get_version("bash", archive="ubuntu", series="resolute",
                             pocket="Release", provider_name="launchpad")
debian = service.get_version("bash", archive="debian", series="sid",
                             pocket="Release", provider_name="launchpad")
print(ubuntu.version_string if ubuntu else "n/a",
      debian.version_string if debian else "n/a")
```

## Common Pitfalls

1. **Skipping `login()`.** Every query needs an active session for that provider.
   Forgetting it (or logging into the wrong provider) raises
   `ValueError: No active session...`. Log into each provider you query.
2. **Treating providers as interchangeable.** Identifier formats and supported
   capabilities differ. A bare bug number works for Launchpad but not GitHub
   (`owner/repo#number`). Load the provider sub-skill first.
3. **Forgetting the `archive` arg** on `get_version` / `get_package`. It's
   required and provider-specific (`"ubuntu"`/`"debian"` for Launchpad; the
   `"https://snapcraft.io/"` base for snaps).
4. **Assuming anonymous GitHub is truly anonymous.** It opportunistically uses
   `GITHUB_TOKEN` or `gh auth token`. Pass an explicit `ProviderCredentials`
   when you need deterministic auth, or expect rate-limiting when none is found.
5. **Expecting ubq to read credential files.** It doesn't — you read the file
   and pass `ProviderCredentials(token=...)`.
6. **Confusing `None` vs `[]`.** `None` = not found (single-item getters); `[]` =
   no matches (search/list methods). Guard both before dereferencing.
7. **Copying signatures from the ubuntu-mcp README.** The MCP wrapper's argument
   names/shapes diverge from ubq's. This skill reflects the real `QueryService`.
8. **Leaking secrets.** Never print/log a token or commit a credentials file.
   Reference credentials by file path; redact any token in output.

## Verification Checklist

- [ ] `ubq` installed (`pip install ubq` / `uv add ubq`); `python -c "from ubq import QueryService; print(QueryService().available_providers())"` prints `('github', 'launchpad', 'snapcraft')`
- [ ] `login()` called for the target provider before any query
- [ ] Correct `provider_name` passed on every call
- [ ] For versions/packages: `archive` argument supplied and provider-appropriate
- [ ] Identifier format matches the provider (checked the sub-skill)
- [ ] Chosen capability is supported by the provider (capability matrix)
- [ ] `None` and `[]` results handled before use
- [ ] Any token sourced from env/file, never hard-coded or logged
