---
name: ubq-github
description: "Use when querying or creating GitHub data through the ubq library's 'github' provider: fetch/search/create issues (modeled as bugs) and fetch pull requests (modeled as merge requests). Covers the owner/repo#number identifier format, GraphQL vs REST behavior, token auth via ProviderCredentials / GITHUB_TOKEN / gh CLI, search-query mapping, and PR review-to-vote conversion. Load the central 'ubq' skill for the shared API and models."
version: 1.0.0
author: Lena Voytek
metadata:
    tags: [ubq, github, issues, pull-requests, bugs, merge-requests, graphql]
    related_skills: [ubq, ubq-launchpad, ubq-snapcraft]
---

# ubq — GitHub Provider (`provider_name="github"`)

## Overview

The GitHub provider maps GitHub concepts onto ubq's generic models:

- **Issues → bugs** (`get_bug`, `search_bugs`, `submit_bug` create an issue).
- **Pull requests → merge requests** (`get_merge_request`,
  `get_merge_requests_from_user`).

It uses GitHub's **GraphQL API** for single-item fetches (issue/PR by number)
and the **REST search API** for searches/listings. There is **no** package or
version capability.

Read the central **`ubq`** skill first for the `QueryService` API, auth modes,
and model shapes. This skill covers GitHub-specific identifiers and semantics.

Capabilities: bug ✅ (issues) · merge_request ✅ (PRs) · version ❌ · package ❌.

## When to Use

- Fetch a specific GitHub issue or PR by `owner/repo#number`.
- Search issues across GitHub by text/label/author/assignee/state/date.
- List a user's pull requests.
- Open a new issue in a repo.

Don't use for: package versions (no capability) or Ubuntu/Debian/Launchpad data
(use `ubq-launchpad`).

## Authentication

```python
from ubq import QueryService
from ubq.models import ProviderCredentials

service = QueryService()

# Explicit token (a GitHub PAT, e.g. ghp_...). Sent as: Authorization: Bearer <token>
service.login(provider_name="github",
              credentials=ProviderCredentials(token="ghp_..."))

# "Anonymous" — but see the fallback chain below.
service.login(provider_name="github")
```

**Important — "anonymous" GitHub is not truly anonymous.** When no
`credentials` are given, the provider looks for a token in this order:

1. `GITHUB_TOKEN` environment variable, then
2. `gh auth token` (the GitHub CLI, 5s timeout), then
3. nothing → requests go out **unauthenticated** and hit GitHub's low anonymous
   rate limit (and can't see private repos).

So results may depend on ambient credentials. Pass an explicit
`ProviderCredentials(token=...)` when you need deterministic behavior. A token is
required to create issues and to read private repos.

Token from a file — use `ProviderCredentials.from_file(path)`:

```python
creds = ProviderCredentials.from_file(cred_file) if cred_file else None
service.login(provider_name="github", credentials=creds)
```

Never log or commit the token.

## Identifier Format

Single issues and PRs are identified by **`owner/repo#number`**, e.g.
`ubuntu/ubq#42`. Parsing (from `ubq.providers.github.common.parse_github_id`):
split on the last `#` for the number, then split `owner/repo` on `/`. A
malformed id raises `ValueError: Invalid ... format '...'. Expected
'owner/repo#number'.`

## Issues (bugs)

### Fetch an issue

```python
service.login(provider_name="github",
              credentials=ProviderCredentials(token=token))
bug = service.get_bug(bug_id="ubuntu/ubq#42", provider_name="github",
                      metadata_only=False)
```

- `metadata_only=True` → GraphQL metadata query: no comments.
- `metadata_only=False` → also fetches up to 100 comments.
- Returns `None` if the issue doesn't exist.
- `BugRecord` mapping: `tags` ← issue labels (first 20); `owner` ← issue author;
  `assignee` ← first assignee (first 5 fetched, only `[0]` kept); `created_at` /
  `updated_at` parsed from ISO-8601. `bug_tasks` is empty for fetched issues.

### Search issues

`BugSearchRecord` fields are translated into GitHub search qualifiers
(`q=is:issue ...`, `per_page=100`):

| BugSearchRecord field | GitHub qualifier |
|-----------------------|------------------|
| `title` | free-text term |
| each `tags[]` | `label:<tag>` |
| `status` | `is:<status>` (e.g. `is:open`, `is:closed`) |
| `assignee.username` | `assignee:<user>` |
| `owner.username` | `author:<user>` |
| `created_since` | `created:>=YYYY-MM-DD` |
| `created_before` | `created:<=YYYY-MM-DD` |
| `modified_since` | `updated:>=YYYY-MM-DD` |

```python
from datetime import datetime
from ubq.models import BugSearchRecord, UserRecord

query = BugSearchRecord(
    provider_name="github",
    title="segfault",
    tags=["bug"],                         # -> label:bug
    status="open",                        # -> is:open
    owner=UserRecord(username="octocat"), # -> author:octocat
    assignee=UserRecord(username="hubot"),# -> assignee:hubot
    created_since=datetime(2026, 1, 1),
)
issues = service.search_bugs(query=query, provider_name="github")
```

Note GitHub's `status` is a search state (`open`/`closed`), unlike Launchpad's
status vocabulary. Search results carry `owner`, `assignee`, `tags`, and dates
(no comments).

### Create an issue (`submit_bug`)

GitHub overloads `package_names[0]` as the **target repo** in `owner/repo` form.

```python
from ubq.models import UserRecord
from ubq.models.bug import BugSubmissionRecord

submission = BugSubmissionRecord(
    provider_name="github",
    title="Crash on startup",
    package_names=["ubuntu/ubq"],         # owner/repo  (REQUIRED, [0] used)
    description="Steps...",               # -> issue body
    tags=["bug", "crash"],                # -> labels
    assignee=UserRecord(username="octocat"),  # -> assignees:[octocat]
)
created = service.submit_bug(submission=submission, provider_name="github")
print(created.id)                          # e.g. ubuntu/ubq#123
```

- `package_names[0]` must be `owner/repo`; otherwise `ValueError`.
- Only `title`, `description`→body, `tags`→labels, and a single `assignee` are
  sent. `importance`, `status`, `milestone`, `subscribers`, `private` have no
  GitHub issue-creation equivalent and are **not** applied. If any of them is
  set, `submit_bug` emits a `UserWarning` naming the ignored fields (rather than
  dropping them silently), then proceeds with the supported fields.
- This is a real write (POST `/repos/{owner}/{repo}/issues`) and needs a token
  with write scope — confirm intent first.

## Pull Requests (merge requests)

### Fetch a PR

`get_merge_request` reuses the generic four-arg signature, but GitHub only needs
three: `author`=repo owner, `project`=repo name, `merge_request_id`=PR number.
**`branch` is ignored** (accepted for interface compatibility). The id must be
an integer string.

```python
pr = service.get_merge_request(
    author="ubuntu",          # repo owner
    project="ubq",            # repo name
    branch="",                # ignored for GitHub — pass ""
    merge_request_id="7",     # PR number (integer string)
    provider_name="github",
)
```

From an `owner/repo#number` string:

```python
owner_repo, number = "ubuntu/ubq#7".split("#", 1)
owner, repo = owner_repo.split("/", 1)
pr = service.get_merge_request(author=owner, project=repo, branch="",
                               merge_request_id=number, provider_name="github")
```

A non-integer `merge_request_id` raises `ValueError`. Returns `None` if the PR
doesn't exist.

### List a user's PRs

```python
prs = service.get_merge_requests_from_user(user_id="octocat",
                                           provider_name="github")
```

Uses REST search `q=type:pr author:<user>`. These records have **no votes**
(the search API omits reviews) and `status` is the raw issue state.

### MergeRequestRecord mapping (GitHub)

- `id` = `owner/repo#number`; `status` = PR state lowercased (`open`/`closed`/…).
- `source_branch` = `headRefName`; `target_branch` = `baseRefName`.
- `author` = PR author; `web_url` = PR URL.
- `assignees` = the PR's actual assignees (GitHub's `assignees` field).
- `votes` come from PR reviews (single-PR fetch only):
  `APPROVED`→ +1 `APPROVE`, `CHANGES_REQUESTED`→ -1 `DISAPPROVE`,
  `COMMENTED`→ 0 `COMMENT`, `PENDING`→ 0 `PENDING`. Reviewers appear here as
  `votes[*].voter`, not under `assignees`.

## Example Programs (source repo `scripts/`)

The ubq source repository ships runnable example programs demonstrating these
calls end to end. They're references, not a runtime dependency — your code calls
the library directly. Operations covered:

- `get_github_issue.py <owner/repo#number> [--show-comments] [--token TOKEN]`
- `get_github_pull_requests.py <owner/repo#number | --user USERNAME> [--token TOKEN]`

## Common Pitfalls

1. **Wrong identifier shape.** Single getters need `owner/repo#number`; a bare
   number or a URL won't parse (`ValueError`).
2. **Passing a branch for a PR.** `get_merge_request` ignores `branch` for
   GitHub — pass `""` and rely on `author`/`project`/`merge_request_id`.
3. **Non-integer PR id.** `merge_request_id` must be an integer string.
4. **Assuming `assignees` = GitHub assignees on PRs.** They're the review voters
   here. Use `author` for the PR author; inspect `votes` for reviewers.
5. **Expecting votes from the user-PR listing.** `get_merge_requests_from_user`
   returns empty `votes`; only the single-PR fetch includes reviews.
6. **Relying on extra submission fields.** Issue creation ignores `importance`,
   `status`, `milestone`, `subscribers`, `private` (it warns via `UserWarning`
   when they're set). Set labels via `tags`.
7. **Silent ambient auth / rate limits.** Without explicit credentials the
   provider may use `GITHUB_TOKEN` or `gh auth token`, or fall back to
   unauthenticated (rate-limited). Pass a token for deterministic results.
8. **GraphQL errors.** A bad query/permissions issue surfaces as
   `RuntimeError: GitHub GraphQL errors: ...`. Timeouts raise
   `ubq.RequestTimeoutError`.

## Verification Checklist

- [ ] `login(provider_name="github", credentials=ProviderCredentials(token=...))` for deterministic auth (or env/gh fallback understood)
- [ ] Single issue/PR ids are `owner/repo#number`
- [ ] PR fetch: `author`=owner, `project`=repo, `branch=""`, integer `merge_request_id`
- [ ] Search `status` uses GitHub states (`open`/`closed`), not Launchpad terms
- [ ] Issue creation: `package_names[0]` is `owner/repo`; write intent confirmed
- [ ] `None` (not found) and `[]` (no matches) handled
- [ ] Token sourced from env/file/secret, never logged or committed
