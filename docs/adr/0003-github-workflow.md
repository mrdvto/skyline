# 3. Issue-driven branches with mandatory pull requests

- **Status:** Accepted
- **Date:** 2026-09-20

## Context

Most work will be done by an AI agent across many short sessions. The
failure mode to design against is accumulated debris: branches nobody
remembers creating, half-finished work with no recorded purpose, and no way
to tell abandoned from in-progress.

Branch *naming* conventions cannot carry this weight. Claude Code web
sessions receive a harness-assigned branch name such as
`claude/blissful-dijkstra-b65fhv`, which the agent cannot choose. A
convention that cannot be followed is not a control.

## Decision

Work follows **issue → branch → pull request**.

The binding rule: **every branch must have an open PR linking to an issue
on its first push.** A branch without a PR is invisible; a PR without an
issue has no recorded reason to exist. This holds regardless of branch
name, which is why it, rather than naming, is the anti-orphan mechanism.

Supporting measures:

- `main` is protected; no direct pushes.
- Head branches delete automatically on merge.
- Abandoning work means closing the PR *and* deleting the branch together.
- Where the name is controllable: `feat/<issue>-<slug>`, `fix/…`, `chore/…`.

### Merge authority

The intended end state is that Claude self-merges once CI passes. That is
deferred: a green check gates nothing until CI runs real lint, typecheck,
tests, and a memory check capable of failing. Until then Claude opens PRs
and the maintainer merges. The switch requires an explicit agreement, not
an assumption.

## Consequences

- Every branch traces to a stated reason; orphans become visible rather
  than accumulating.
- Slight overhead per unit of work — an issue must exist first.
- Issue history doubles as a project changelog and a record of intent.
- The merge-authority switch must be revisited once CI is real, or the
  project silently keeps a slower process than intended.
