# Contributing to Skyline

Skyline is in early development with a single maintainer. Outside
contributions aren't being solicited yet, but the workflow below is what
the project follows now and what it will expect when it opens up.

## Workflow

Work is **issue-driven**:

1. **Open or find an issue.** Everything starts here — it's the record of
   why a change exists.
2. **Branch.** Where you choose the name: `feat/<issue>-<slug>`,
   `fix/<issue>-<slug>`, or `chore/<issue>-<slug>`.
3. **Open a draft PR on your first push**, with `Closes #<issue>` in the
   body. Not later — the first push. A branch without a PR is invisible to
   everyone else.
4. **Get CI green.**
5. **Mark ready for review.**

`main` is protected and always deployable. Head branches are deleted
automatically on merge.

Abandoning work? Close the PR *and* delete the branch, together.

Dependabot is the one exception to step 1. Its branches carry no issue,
because the diff and the changelog links in the PR body already say why the
change exists. Those PRs are reviewed and merged like any other.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/):
`type(scope): summary`

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`,
`build`, `ci`. Scope is the module — `feat(calendar):`,
`fix(sync/google):`, `perf(kiosk):`.

Explain *why* in the body whenever the diff doesn't make it obvious.

## Code style

Skyline follows [ponytail](https://github.com/DietrichGebert/ponytail)
(MIT). It is not vendored here, so install it yourself if you want the
agent-enforced version. The rule stands either way.

Before writing anything, check whether it needs to exist, whether this
codebase already has it, whether the standard library or the platform
covers it, and whether an installed dependency already does the job. Write
the smallest thing that works.

It pairs well with the 1GB budget, since the cheapest dependency is the one
never added.

It does not apply to validation at trust boundaries, error handling that
prevents data loss, security, or accessibility. Those get written properly.

A shortcut taken on purpose gets a comment naming its ceiling and the way
out:

```python
# ponytail: linear scan, index it if events pass a few thousand
```

## The memory budget

Skyline's hardware floor is a **1GB Raspberry Pi 4**
([ADR-6](docs/adr/0006-1gb-pi4-hardware-floor.md)). This is the constraint
most likely to make an otherwise good change unacceptable.

Before adding a dependency, check what it costs to import. Some specifics
that already bind:

- `google-auth` + `httpx` against Google's REST endpoints — **not**
  `google-api-python-client`, which loads large discovery documents into
  memory.
- `aiosqlite` rather than an ORM.

If a change raises steady-state RSS, say so in the PR with numbers. Memory
regressions are treated as bugs, not trade-offs to discuss later.

## Offline-first

The UI must never block on a remote API, and must stay useful with no
internet. Local SQLite is the read path; background workers reconcile with
Google Calendar, CalDAV, and Home Assistant. No screen may show a spinner
that's waiting on the network.

## Licensing

Skyline is **AGPL-3.0-or-later**. Every source file starts with:

```python
# SPDX-License-Identifier: AGPL-3.0-or-later
```

`scripts/check_spdx.py` enforces this in CI, on `.py`, `.sh`, `.js`,
`.ts`, `.svelte`, `.yml`, `.yaml` and `.toml`. The script says which files
are out of scope and why.

Contributions are accepted under the same license. There is no CLA; the
sign-off on your commit (`git commit -s`, per the
[Developer Certificate of Origin](https://developercertificate.org/)) is
your statement that you have the right to submit the work.

Dependencies must be license-compatible. **GPLv2-only and proprietary
licenses cannot be used.** Permissive (MIT/BSD/Apache-2.0), LGPL, GPLv3,
and AGPLv3 are fine. If the library you want is incompatible, raise it
rather than working around it.

## Secrets

Never commit credentials, tokens, or OAuth secrets — including in tests and
examples. If you find one committed, report it rather than quietly
rewriting history.

## Architecture decisions

Significant decisions live in [`docs/adr/`](docs/adr/). Read them before
proposing something that contradicts one. Changing a decision means a new
ADR superseding the old one — the record isn't edited after the fact.
