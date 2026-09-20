# Skyline — Operating Guide for Claude

Read this before doing anything in this repository.

## What Skyline is

A family organization system — shared calendar, to-dos, and household
coordination — running on a Raspberry Pi with an attached touch monitor.
Self-hosted, offline-first, and free software.

The Pi is a **kiosk appliance**: it boots straight into a fullscreen browser
showing the Skyline web app, served by a local backend on the same device.
Because it's a web app, phones and tablets on the LAN get access for free.

## Hard constraints

These are not preferences. Violating them means the work is wrong.

| Constraint | Value |
|---|---|
| Hardware floor | Raspberry Pi 4, **1GB RAM** |
| License | AGPL-3.0-or-later |
| Backend | Python 3.11+ / FastAPI |
| Frontend | Svelte |
| Database | SQLite (WAL mode) |
| Display | Chromium kiosk (swappable for `cog`) |

### The 1GB budget

Total system RAM is 1024MB. The working budget:

| Component | Ceiling |
|---|---|
| OS + kiosk compositor | 180MB |
| Browser | 500MB |
| Backend (Python, SQLite, sync workers) | 200MB |
| GPU split | 50MB |
| Headroom | ~90MB |

Consequences that bind every change:

- **Prefer lean dependencies.** Before adding any library, check its import
  cost. Specifically: use `google-auth` + `httpx` against Google's REST
  endpoints, **not** `google-api-python-client` (it loads large discovery
  documents into memory). Prefer `aiosqlite` over an ORM.
- **Never assume swap.** Swapping to the SD card destroys both performance
  and the card. `zram` only.
- **Memory regressions are bugs.** If a change raises steady-state RSS,
  say so in the PR, with numbers.

### Offline-first is mandatory

The UI must never block on a remote API and must stay useful when the WAN
is down. Local SQLite is the read path; background workers reconcile
against Google Calendar, CalDAV, and Home Assistant. No screen may render
a spinner that waits on the internet.

## GitHub workflow

### The rule that prevents orphaned branches

Every branch must, **on its first push**, have an open pull request that
links to a GitHub issue. Not the second push. Not before merge. The first.

That single rule is what keeps the repository clean, and it is the one to
enforce most strictly. A branch with no PR is invisible; a PR with no issue
has no recorded reason to exist.

Honest caveat: Claude Code web sessions are assigned a branch name by the
harness (for example `claude/blissful-dijkstra-b65fhv`), and that name
cannot be chosen. So branch *naming* cannot be the anti-orphan mechanism —
the PR-and-issue-on-first-push rule is. When the branch name *is* under
Claude's control, use `feat/<issue>-<slug>`, `fix/<issue>-<slug>`, or
`chore/<issue>-<slug>`.

### Sequence for any unit of work

1. Find or open a GitHub issue describing the work.
2. Branch (or use the harness-assigned branch).
3. Commit.
4. Push and immediately open a **draft** PR whose body contains
   `Closes #<issue>`.
5. Get CI green.
6. Mark ready for review.

### Merging

**Claude does not merge to `main` right now.** The agreed end state is that
Claude self-merges once CI passes — but that only becomes safe when CI
genuinely gates something. Until the pipeline runs real lint, typecheck,
tests, and a memory check that can actually fail, "green" is vacuous.

Claude may flip to self-merge only after proposing it explicitly and the
maintainer agreeing. Until then: open the PR, get it green, stop.

`main` is always deployable. Never push to it directly.

### Branch hygiene

- Head branches delete automatically on merge (repository setting).
- Abandoned work gets its PR closed **and** its branch deleted in the same
  action. Never leave one without the other.
- Before starting a session, check for stale branches with no open PR and
  raise them rather than adding to the pile.

## Commits

Conventional Commits: `type(scope): summary`.

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `build`,
`ci`. Scopes follow top-level modules, e.g. `feat(calendar):`,
`fix(sync/google):`, `perf(kiosk):`.

Explain *why* in the body when the reason isn't obvious from the diff.

## Licensing requirements

Every source file carries an SPDX identifier at the top:

```python
# SPDX-License-Identifier: AGPL-3.0-or-later
```

Before adding a dependency, check its license. **GPLv2-only and
proprietary licenses are incompatible** and must be refused — raise it
rather than working around it. Permissive (MIT/BSD/Apache-2.0), LGPL,
GPLv3, and AGPLv3 are fine.

## Secrets

No credentials, tokens, or OAuth secrets in the repository — ever, not even
in tests or examples. Runtime secrets live outside version control and are
referenced through configuration. If a secret is found committed, stop and
report it; do not quietly rewrite history.

## Ask before proceeding

Stop and raise these rather than deciding unilaterally:

- Schema changes that require a migration
- New runtime dependencies with meaningful memory cost
- Anything altering the Google OAuth or credential-storage design
- Changes to the kiosk boot path (a bad one bricks the appliance for a
  non-technical family)
- Architectural decisions worth an ADR

## Architecture decisions

Significant decisions are recorded in `docs/adr/`. Read them before
proposing anything that contradicts one. Changing a decision means writing
a new ADR that supersedes the old one, not editing history.
