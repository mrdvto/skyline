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
| Display | Chromium (swappable for `cog`) in `cage` |
| Appliance OS | Raspberry Pi OS Lite, 64-bit |

Two of those rows record a current decision rather than an immovable one.
[ADR-12](docs/adr/0012-raspberry-pi-os-lite-and-cage.md) keeps `labwc` as a
documented fallback if `cage` fights us, and says a 32-bit reflash is the
experiment to run if the memory budget fails on arm64. Proposing either is
not a violation; silently changing the kiosk boot path is.

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
  cost. Specifically: use `httpx` against Google's REST endpoints, **not**
  `google-api-python-client`. Prefer `aiosqlite` over an ORM.

  The parenthetical that used to sit here said
  `google-api-python-client` loads large discovery documents into memory.
  The spike for #29 measured that and it is not true: the Calendar
  discovery document costs 0.61MB, and the two stacks land on the same
  figure. The rule survives for other reasons, which are in
  [ADR-13](docs/adr/0013-google-calendar-authorization-flow.md) along with
  the finding that `google-auth` is nearly the whole cost and probably
  should go too. ADR-13 is Proposed, so `google-auth` is not banned yet --
  but do not repeat the discovery-document reason, it was never measured.

  `CONTRIBUTING.md` and `docs/sdd.md` §5.2 carried the same claim. They are
  corrected too. A rule that says "do not repeat this" is worth nothing
  while another file in the same repository still says it, which is what
  shipped in the first commit of #32 and is the reason this note exists.
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

### Replies in chat

Brief. Answer, then stop. No preamble, no recap of what was just done unless
it changed, no restating the question. Bullets over paragraphs, and grammar
comes second to being short.

Brevity is not omission. Say when something is uncertain, when a claim was not
verified, and when the maintainer is wrong. Those earn their words; a summary
of work they just watched does not.

This is separate from the standards below, which govern code and prose that
land in the repository. It restates the maintainer's account-level preference
so it still applies in sessions running without that account; if the two ever
disagree, the account preference wins.

### Code and prose that ship

Two standards, and they now live in different places.

ponytail is vendored into `.claude/skills/`, so it loads for anyone with
this checkout. It moved here because upstream ships it as a Claude Code
plugin, and a plugin installed on one machine does not follow you into a
remote session -- web sessions were running without it and applying the
ladder from memory. `.claude/skills/README.md` records where the copy came
from and how to re-sync it.

humanizer is still an account-scoped claude.ai skill. A contributor will
not have it, and neither will a session running without the maintainer's
account. Check the session's skill list rather than assuming.

Use the name that actually invokes the skill. The vendored copies load
under bare names -- `ponytail`, `ponytail-review`, `ponytail-audit`,
`ponytail-debt` -- but humanizer is namespaced, and
`anthropic-skills:humanizer` is the name that resolves. Plain `humanizer`
does not. This is not pedantry: a session reported humanizer missing and
wrote the prose by hand while the skill sat in its list under the longer
name. Read the list before concluding a tool is absent, and match the name
character for character.

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

The vendored copy also brings `ponytail-review` (a diff read for
over-engineering), `ponytail-audit` (the same, repository-wide), and
`ponytail-debt`, which collects the `ponytail:` markers above into a ledger
-- the part this file has always asked for and nothing did.

### Prose: humanizer

Comments, documentation, commit bodies, and PR descriptions go through the
`anthropic-skills:humanizer` skill: plain sentences, concrete detail, no promotional filler.
It is account-scoped, so a session may not have it. Write plainly if it is
not loaded; the sentence above is the whole of it.

### Text that is not ours: fetch it, never recall it

Any text belonging to someone else -- a licence, a code of conduct, a
spec, a config another project publishes -- gets fetched from its source.
Never reproduced from memory.

`CODE_OF_CONDUCT.md` is Contributor Covenant 3.0, which differs from 2.1
in its section names, its enforcement model and its licence (CC BY-SA 4.0
rather than CC BY 4.0). Writing it from recall would have produced
something that looked right and carried the real upstream attribution
block while not being the document it named. That is a forgery of a
licensed text, not a typo.

`raw.githubusercontent.com` is reachable from a remote session, which is
how that file got its real contents. If a text cannot be fetched, say so
and stop, rather than approximating it.

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

**Run any command you write into documentation, and paste the run into the
PR.** CI cannot execute a command that lives in prose, so nothing catches a
wrong one except running it. #24 added `--prune` to the post-merge fetch and
left the branch argument on, which confines pruning to that refspec and clears
nothing. It read as correct, it had a paragraph explaining why it was there,
and it was merged without ever being run. Where a command is supposed to
change something, check the thing before and after, not just the exit code.

**Run `ponytail-review` on the diff before pushing, and `pr-critic` before
marking a PR ready.** ponytail-review is vendored in `.claude/skills/`, so it
is available in every session, and it costs one pass. The `pr-critic` agent in
`.claude/agents/` is the wider version of the same idea: one pass, blocking and
non-blocking findings, no score and no loop. Its own description says when to
run it, but that is an invocation hint rather than a rule, which is why the
timing is written here too. A
scored critic run in a loop was considered and rejected, because iterating
until a reviewer is satisfied optimises for the reviewer rather than for
correctness, and a second model reading the same diff shares the first one's
blind spots. Neither replaces running the thing.

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
git fetch --prune origin && git checkout -B <branch> origin/main
```

`--prune` is not decoration. Head branches delete on merge, so without it
`origin/<branch>` survives locally, pointing at the pre-merge commit. Anything
that compares `HEAD` against `origin/<current-branch>` then reports commits
that are already on the remote as unpushed, which is what the Claude Code stop
hook did after #22.

The fetch takes no branch argument on purpose. `--prune` only removes refs
covered by the refspec being fetched, so `git fetch --prune origin main`
prunes nothing outside `main` and leaves the stale ref exactly where it was.
That is what #24 shipped, and #25 is it being caught.

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

`.claude/skills/` holds a verbatim copy of ponytail, which is MIT and
therefore compatible. Its licence and provenance sit beside it. Vendored
files are not edited locally: an edit turns the next re-sync into a merge,
and a standard everyone else reads differently is not a standard.

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
- **Outbound HTTPS is filtered.** `gnu.org`, `raspberrypi.com`,
  `downloads.raspberrypi.com`, `developers.google.com` and
  `console.cloud.google.com` fail at the proxy tunnel. Blocking happens at
  `CONNECT`, before any path is visible, so it is whole hosts rather than
  paths. `api.github.com` is different: it connects and answers, then refuses
  at the application layer, so a session that probes it sees a 200 and should
  still use the GitHub tools. Working: git clones from `github.com`, fetches
  from `raw.githubusercontent.com`, and Google's OAuth and API hosts --
  `accounts.google.com`, `oauth2.googleapis.com` and `www.googleapis.com` all
  answer. Google's *documentation* is the part that does not, which is a
  sharper edge than it sounds: a question about Google's API can be tested
  against the live endpoint but not read about, so anything the endpoint will
  not answer has to be left open rather than recalled. #29 hit this and said
  so rather than guessing. It is also why gitleaks cannot be tested locally,
  and why the Pi release version in
  [ADR-12](docs/adr/0012-raspberry-pi-os-lite-and-cage.md) has to come off the
  hardware rather than the vendor's site.
- **The container is ephemeral.** Anything uncommitted disappears when it
  is reclaimed. Tooling that should survive belongs in this repository or
  in an account-scoped skill, never installed into the session and left
  there.

## Architecture decisions

Significant decisions are recorded in `docs/adr/`. Read them before
proposing anything that contradicts one. Changing a decision means writing
a new ADR that supersedes the old one, not editing history.
