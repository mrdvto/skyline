# Skyline — Operating Guide for Claude

Read this before doing anything in this repository.

## What Skyline is

A family organization system — shared calendar, to-dos, and household
coordination — running on a Raspberry Pi with an attached touch monitor.
Self-hosted, offline-first, and free software.

The Pi is a **kiosk appliance**: it boots straight into a fullscreen browser
showing the Skyline web app, served by a local backend on the same device.
Because it's a web app, phones and tablets on the LAN get access for free.

Where the project currently stands, and what is next, lives in the GitHub
issues. This file holds the rules, which change far less often than the
state does.

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

## How to write

Both standards below live outside this repository, as account-scoped
claude.ai skills. Nothing here enforces them. A session running without the
maintainer's account will not load either one, and contributors will not
have them. That is a deliberate trade: the repository stays free of vendored
third-party content, at the cost of the standard not being self-describing.
If either standard has to outlive one account, it moves into the repo.

### Code: ponytail

Code follows [ponytail](https://github.com/DietrichGebert/ponytail) (MIT).
It is a ladder you climb before writing anything: does this need to exist,
does the codebase already have it, does the stdlib do it, does the platform
do it natively, does an installed dependency cover it, can it be one line.
Stop at the first rung that holds.

This happens to pay Skyline's memory budget for free. The cheapest
dependency is the one never added, and `<input type="date">` costs nothing
that a date-picker library costs.

What it never trims: input validation at trust boundaries, error handling
that prevents data loss, security, accessibility. Cutting those is not
laziness, it is a bug with a deadline.

Deliberate shortcuts get a `ponytail:` comment naming the ceiling and the
way out, so the markers can be collected later instead of rotting:

```python
# ponytail: linear scan, index it if events pass a few thousand
```

If the skill is not loaded in a session, follow the ladder anyway. It is
short enough to apply from the paragraph above.

### Prose: humanizer

Comments, documentation, commit bodies, and PR descriptions go through the
`humanizer` skill: plain sentences, concrete detail, no promotional filler.
Same caveat as above, and the same fallback. Write plainly if it is not
loaded.

## GitHub workflow

### The rule that prevents orphaned branches

Every branch must, **on its first push**, have an open pull request that
links to a GitHub issue. Not the second push. Not before merge. The first.

That single rule is what keeps the repository clean, and it is the one to
enforce most strictly. A branch with no PR is invisible; a PR with no issue
has no recorded reason to exist.

The rule covers branches a person or Claude opens. Automated dependency
branches (`dependabot/*`) are exempt: no bot files an issue first, and an
issue per bump would be paperwork nobody reads. The diff and the changelog
links in the bot's PR body are the record.

Those PRs are reviewed and merged by the maintainer like any other. Nothing
auto-merges on green, for the same reason Claude does not merge: the
pipeline is linters, so "green" does not yet mean the bump is safe. Worth
revisiting once CI runs tests.

The SessionStart hook needs no exemption. Its orphan warning lists *local*
branches with no upstream, and a `dependabot/*` branch only ever exists on
the remote, so it never appears there.

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

### Verifying before you push

CI runs the checks below. Run them first. A push that turns CI red costs a
round trip and, once there are reviewers, some of their patience.

```
pip install -r requirements-ci.txt
shellcheck .claude/hooks/*.sh
actionlint
python3 scripts/check_yaml.py
python3 scripts/check_docs.py
python3 scripts/check_spdx.py
```

Neither `shellcheck` nor `actionlint` is preinstalled in remote sessions,
which is what `requirements-ci.txt` is for -- it pins the versions CI
uses, so a local run and a CI run agree. The gitleaks step runs only in
CI, because its binary cannot be fetched here, so it is the one check that
lands unverified.

**Read the log of any check you added or changed, even when it passes.** A
green tick says a command exited 0, not that it did what you think. The
first CI run on this repository passed while the comment on its own
gitleaks step described behaviour the step was not performing; reading the
log caught it, the green tick did not.

**Break a new check on purpose once and confirm it fails.** A check that
cannot fail gates nothing, and a pipeline of those is worse than none,
because it looks like coverage.

### Merging

**Claude does not merge to `main` right now.** The agreed end state is that
Claude self-merges once CI passes — but that only becomes safe when CI
genuinely gates something. Until the pipeline runs real lint, typecheck,
tests, and a memory check that can actually fail, "green" is vacuous.

Claude may flip to self-merge only after proposing it explicitly and the
maintainer agreeing. Until then: open the PR, get it green, stop.

`main` is always deployable. Never push to it directly.

### After the branch's PR merges

A merged pull request is finished. It cannot track new work, and commits
stacked on top of merged history do not belong to anything.

So when the designated branch's PR has merged, restart the branch from the
default branch rather than continuing on it, keeping the same name:

```
git fetch origin main && git checkout -B <branch> origin/main
```

Any PR opened afterwards is a new PR against a new issue. If the branch
still carries unmerged commits, rebase them onto the new base instead of
discarding them.

The SessionStart hook detects this case and says so at session open, but
check it yourself if the hook has not run.

### Branch hygiene

- Head branches delete automatically on merge (repository setting).
- Abandoned work gets its PR closed **and** its branch deleted in the same
  action. Never leave one without the other.
- Before starting a session, check for stale branches with no open PR and
  raise them rather than adding to the pile. The SessionStart hook in
  `.claude/hooks/` prints these, prunes refs for branches deleted on merge,
  and flags a branch that needs restarting.

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

`scripts/check_spdx.py` checks this in CI, on `.py`, `.sh`, `.js`, `.ts`,
`.svelte`, `.yml`, `.yaml` and `.toml`. What it skips, and why, is written
into the script. Adding a language means adding it there.

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
- Where third-party tooling lives: vendored into this repository, an
  account-scoped skill, or a local install. Cheap to reverse and therefore
  tempting to just decide, but reversing it leaves visible churn in the
  history

## This environment

True of remote sessions. A local checkout will differ, so check rather than
assume.

- **No `gh` CLI.** Use the GitHub tools for issues, pull requests, checks,
  and job logs.
- **Outbound HTTPS is filtered.** `api.github.com` and `gnu.org` are
  blocked; git clones from `github.com` and fetches from
  `raw.githubusercontent.com` work. This is why gitleaks cannot be tested
  locally.
- **The container is ephemeral.** Anything uncommitted disappears when it
  is reclaimed. Tooling that should survive belongs in this repository or
  in an account-scoped skill, never installed into the session and left
  there.

## Architecture decisions

Significant decisions are recorded in `docs/adr/`. Read them before
proposing anything that contradicts one. Changing a decision means writing
a new ADR that supersedes the old one, not editing history.
