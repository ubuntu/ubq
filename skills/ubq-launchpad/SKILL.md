---
name: ubq-launchpad
description: "Use when querying or submitting Launchpad data through the ubq library's 'launchpad' provider: fetch/search/submit bugs, get Ubuntu/Debian package versions (with changelog) and packages, and read branch merge proposals. Covers Launchpad identifier formats, the archive/series/pocket model, valid bug statuses/importances, anonymous vs OAuth-token auth, and the exact QueryService calls. Load the central 'ubq' skill for the shared API and models."
version: 1.0.0
author: Lena Voytek
metadata:
    tags: [ubq, launchpad, ubuntu, debian, bugs, packages, versions, merge-proposals]
    related_skills: [ubq, ubq-github, ubq-snapcraft, ubq-upstream]
---

# ubq — Launchpad Provider (`provider_name="launchpad"`)

## Overview

The Launchpad provider is the most capable in ubq: it reads **bugs**,
**package versions** (with changelog), **packages**, and **branch merge
proposals**, and can **submit bugs**. It wraps `launchpadlib` against the
production Launchpad instance (`https://api.launchpad.net/devel/`).

Read the central **`ubq`** skill first for the `QueryService` API, the auth
modes, and the model shapes. This skill covers Launchpad-specific identifiers,
arguments, and field semantics.

Capabilities: bug ✅ · version ✅ · package ✅ · merge_request ✅ (full house).

## When to Use

- Fetch a Launchpad bug by number, or search bugs by text/tag/owner/status/etc.
- Look up the published version of a deb source package in a given Ubuntu or
  Debian series + pocket, optionally diffing changelogs.
- Resolve a source package's Launchpad page.
- Read a branch merge proposal or list a user's proposals.
- Submit a new Launchpad bug against one or more Ubuntu packages.

Don't use for: snap versions (use `ubq-snapcraft`) or GitHub issues/PRs (use
`ubq-github`).

## Authentication

```python
from ubq import QueryService
from ubq.models import ProviderCredentials

service = QueryService()

# Anonymous, read-only. A true credential-free login (no keyring, no browser).
service.login(provider_name="launchpad")

# Authenticated (required to submit bugs / read private data).
# token is a launchpadlib OAuth credentials STRING (multi-line blob).
service.login(
    provider_name="launchpad",
    credentials=ProviderCredentials(token=oauth_string),
)
```

> **Anonymous login is non-interactive and safe for automation.** ubq logs in via
> `Launchpad.login_anonymously("ubq", service_root="production", ...)`, which
> obtains read-only access without any credentials — no system keyring access, no
> OAuth authorize step, no browser. It works unattended on servers, CI,
> containers, and automated agents. Anonymous sessions can read public data but
> cannot submit bugs or read private data; pass an OAuth token for those.

Token from a file — use `ProviderCredentials.from_file(path)` (reads the file,
strips whitespace; raises `FileNotFoundError`/`ValueError` on missing/empty):

```python
credentials = ProviderCredentials.from_file(cred_file) if cred_file else None
service.login(provider_name="launchpad", credentials=credentials)
```

Notes:

- The token is the launchpadlib OAuth credentials blob produced by
  `launchpadlib` (consumer key + access token), parsed via
  `Credentials.from_string(token)` — **not** a simple API key.
- A malformed blob raises `lazr.restfulclient.errors.CredentialsFileError`
  during `login`. Catch it; never print the token.
- Anonymous sessions cannot submit bugs (no write access).

## Bugs

### Fetch a bug by id

Launchpad bug id is a **bare number** (string), e.g. `"1993329"`.

```python
service.login(provider_name="launchpad")
bug = service.get_bug(bug_id="1993329", provider_name="launchpad",
                      metadata_only=False)
```

- `metadata_only=True` → fast: title, description, tags, and the four date
  fields only (no comments, no tasks).
- `metadata_only=False` → also fetches `comments` (visible messages only) and
  `bug_tasks` (one per affected package/target). Each extra task is a separate
  Launchpad request, so this is slower.
- Returns `None` if the bug id doesn't exist.

`BugRecord` dates from Launchpad: `created_at` (date_created), `updated_at`
(date_last_updated), `last_message_at` (date_last_message), `last_patch_at`
(latest_patch_uploaded).

Affected packages live on `bug.bug_tasks[*].package_name`:

```python
packages = [t.package_name for t in bug.bug_tasks if t.package_name]
```

### Search bugs

Build a `BugSearchRecord` and call `search_bugs`. All fields are optional;
omitted fields aren't constrained. Tags are combined with **All** (AND).

```python
from datetime import datetime
from ubq.models import BugSearchRecord, UserRecord

query = BugSearchRecord(
    provider_name="launchpad",
    title="apport",                       # maps to search_text
    tags=["regression"],                  # ALL tags must match
    owner=UserRecord(username="someuser"),
    assignee=UserRecord(username="otheruser"),
    milestone="ubuntu-24.04",
    status="New",                         # must be a valid status (below)
    importance="High",                    # must be a valid importance (below)
    created_since=datetime(2026, 1, 1),
    created_before=datetime(2026, 12, 31),
    modified_since=datetime(2026, 6, 1),
)
bugs = service.search_bugs(query=query, provider_name="launchpad")
```

- `owner` / `assignee` are `UserRecord(username=...)` — the username is resolved
  to a Launchpad person.
- `milestone` is resolved against the `ubuntu` distribution.
- Results are de-duplicated by bug id and returned as metadata-level
  `BugRecord`s (no comments/tasks).
- Invalid `status` or `importance` raises `ValueError` before any network call.

### Submit a bug

Requires an authenticated session and at least one **Ubuntu** package.

```python
from ubq.models import UserRecord
from ubq.models.bug import BugSubmissionRecord

submission = BugSubmissionRecord(
    provider_name="launchpad",
    title="bash crashes on startup",
    package_names=["bash"],               # package_names[0] = initial target;
                                          # extras become additional bug tasks
    description="Steps to reproduce ...",
    importance="High",                    # validated
    status="New",                         # validated
    tags=["crash"],
    assignee=UserRecord(username="someuser"),
    subscribers=[UserRecord(username="watcher")],
    private=False,                        # True => information_type="Private"
    milestone=None,
)
created = service.submit_bug(submission=submission, provider_name="launchpad")
print(created.id, created.title)
```

Behavior:

- The bug is created against `package_names[0]`; each further package is added
  as another bug task. A package not found in Launchpad raises `ValueError`.
- `status`/`importance`, if given, are applied to the tasks and must be valid.
- `assignee`/`milestone` are applied to the created task(s); `subscribers` are
  subscribed.
- Submitting is a real external write — confirm intent and inputs first.

### Valid bug statuses and importances

```
Statuses:    New, Incomplete, Opinion, Invalid, Won't Fix, Expired,
             Confirmed, Triaged, In Progress, Deferred, Fix Committed,
             Fix Released, Does Not Exist, Unknown
Importances: Unknown, Undecided, Critical, High, Medium, Low, Wishlist
```

Passing anything else to `search_bugs` or `submit_bug` raises `ValueError`.

## Versions

`get_version(package_name, archive, series, pocket, provider_name)` returns the
**latest Published source** for that exact package in that series+pocket.

```python
v = service.get_version(
    package_name="bash",
    archive="ubuntu",        # distribution: "ubuntu" or "debian"
    series="resolute",       # Ubuntu series codename, or Debian series e.g. "sid"
    pocket="Release",        # see valid pockets below
    provider_name="launchpad",
)
print(v.version_string, v.changelog)     # v is None if nothing Published
```

- `archive` is the **distribution name** for Launchpad: `"ubuntu"` or
  `"debian"` (it maps to that distro's `main_archive`).
- `series` is the series name/codename (`getSeries(name_or_version=series)`).
- **Valid pockets**: `Release`, `Updates`, `Proposed`, `Backports`, `Security`.
  Any other value (including `None`) raises `ValueError`.
- `VersionRecord` includes `changelog` (fetched over HTTP from Launchpad's
  changelog URL), `created_at` (date_created) and `released_at` (date_published).
- Returns `None` if no Published source matches.

Changelog diff pattern (Ubuntu vs Debian):

```python
import difflib
ubuntu = service.get_version("bash", "ubuntu", "resolute", "Release", "launchpad")
debian = service.get_version("bash", "debian", "sid", "Release", "launchpad")
if ubuntu and debian:
    print("".join(difflib.unified_diff(
        (debian.changelog or "").splitlines(keepends=True),
        (ubuntu.changelog or "").splitlines(keepends=True),
        fromfile="debian", tofile="ubuntu")))
```

## Packages

`get_package(package_name, archive, provider_name)` resolves a source package in
a distribution.

```python
pkg = service.get_package(package_name="bash", archive="ubuntu",
                          provider_name="launchpad")
print(pkg.name, pkg.package_url)         # package_url = Launchpad web_link
```

`archive` is again the distribution (`"ubuntu"`/`"debian"`). Returns `None` if
the package isn't found.

## Merge Requests (branch merge proposals)

A Launchpad merge proposal is identified by **four parts** that map to the URL
`~<author>/<project>/<branch>/+merge/<id>`.

```python
mr = service.get_merge_request(
    author="example-user",      # WITHOUT the leading "~"
    project="example-project",
    branch="main",
    merge_request_id="12345",
    provider_name="launchpad",
)
```

Parsing a full identifier string `~author/project/branch/+merge/id`:

```python
identifier = "~example-user/example-project/main/+merge/12345".strip("/")
author_part, rest = identifier.split("/", 1)
author = author_part.lstrip("~")
project, branch, merge_marker, mr_id = rest.rsplit("/", 3)
assert merge_marker == "+merge"
```

List a user's proposals:

```python
mrs = service.get_merge_requests_from_user(user_id="example-user",
                                           provider_name="launchpad")
```

`MergeRequestRecord` notes specific to Launchpad:

- `title` is empty (`""`) — Launchpad proposals have no title field; use
  `description`, `web_url`, branches, or `id`.
- `id` is the proposal's API path (self_link minus the API base).
- `status` is the `queue_status` (e.g. "Needs review", "Merged").
- `assignees` are the requested reviewers; `votes` are derived from review
  comments (`vote_value`: +1 Approve, -1 Needs Fixing/Disapprove/Needs
  Resubmitting, 0 otherwise).
- `added_lines`/`removed_lines` come from the preview diff when available.
- `source_branch`/`target_branch` are git paths (`source_git_path` /
  `target_git_path`).

## Example Programs (source repo `scripts/`)

The ubq source repository ships runnable example programs — one per operation —
that demonstrate these calls end to end. They're examples for reference, not a
runtime dependency (your code calls the library directly). If you have a source
checkout, run them with your project's Python/runner. Operations covered:

- `get_launchpad_bug.py <bug_id> [--show-comments] [--credentials-file FILE]`
- `get_bug_packages.py <bug_id> [--credentials-file FILE]`
- `search_launchpad_bugs.py [--title ... --tag ... --status ... ...]`
- `submit_lp_bug.py --title T --package P [--importance ... --private ...]`
- `get_ubuntu_package_version.py <package> [series]`
- `get_ubuntu_package_info.py <package>`
- `get_launchpad_merge_request.py <~author/project/branch/+merge/id>`
- `get_launchpad_merge_requests.py <launchpad_user_id>`

These are the canonical, copy-pasteable usage references.

## Common Pitfalls

1. **Including the `~` in `author`.** `get_merge_request(author=...)` wants the
   bare username; strip the leading `~` from a `~user/...` identifier.
2. **Invalid pocket.** `get_version` rejects anything outside
   `Release/Updates/Proposed/Backports/Security` (and rejects `None`) with
   `ValueError`. Default to `"Release"` if unsure.
3. **Using `archive="..."` as an archive name.** For Launchpad `archive` is the
   **distribution** (`"ubuntu"`/`"debian"`), not a PPA or pocket.
4. **Expecting a non-empty MR `title`.** Launchpad proposals have none; it's
   always `""`. Don't key UI/logic on it.
5. **Submitting bugs anonymously.** Writes need an OAuth-token session; anonymous
   login can only read.
6. **Invalid status/importance strings.** Must match the valid sets exactly
   (case-sensitive, e.g. `"In Progress"`, `"Fix Released"`).
7. **`metadata_only=False` cost.** Fetching comments + per-task data multiplies
   requests. Use `metadata_only=True` when you only need headline fields.
8. **Slow/unreachable Launchpad.** Long calls can raise
   `ubq.RequestTimeoutError` (default 30s). Raise `QueryService(timeout=...)` for
   big bugs/changelogs.

## Verification Checklist

- [ ] `login(provider_name="launchpad")` (anonymous) or with OAuth token (writes)
- [ ] Bug ids are bare numeric strings
- [ ] `get_version` uses a valid pocket and a distribution `archive`
- [ ] MR `author` has no leading `~`; all four MR parts supplied
- [ ] `status`/`importance` (search & submit) are in the valid sets
- [ ] `None` (not found) and `[]` (no matches) handled
- [ ] Bug submission inputs reviewed; first package exists; intent confirmed
- [ ] OAuth token sourced from file/secret, never logged or committed
