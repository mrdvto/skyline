# 7. Secret scanning runs on pull requests only

- **Status:** Accepted
- **Date:** 2026-09-20

## Context

CI runs on `pull_request` and on `push` to `main`. The gitleaks step did
real work on the first and nothing at all on the second, and reported
success either way.

gitleaks-action builds its commit range with
`git log -p -U0 --no-merges --first-parent <base>^..<head>`. Every commit on
`main`'s first-parent line is a merge commit, because every pull request
lands as "Merge pull request #N". So `--no-merges` throws the whole range
away and the scan has no input:

```
git log --first-parent --no-merges ac187bc..main    # prints nothing
```

Two runs on `main` confirmed it, one on each side of the v2.3.9 -> v3.0.0
bump: both printed `0 commits scanned. scanned ~0 bytes (0)`, then
`no leaks found`. The versions behave identically; the cause is the shape
of the history.

Coverage was never the problem. The `pull_request` runs scan real content
(PR #14's final run: 4 commits, ~26 kB), and every commit in the repository
was scanned by the run that added it. The defect was a green tick
certifying nothing on half the trigger surface.

Two ways out. Drop the scan on push, or give a push scan a job worth doing
— which means scanning full history, a guarantee the pipeline has never
made and a different promise than repairing this one.

## Decision

The secret scan runs on pull requests only, gated by
`if: github.event_name == 'pull_request'`. The other five checks still run
on push to `main`, so a merge commit is still verified.

Full-history scanning is not adopted here. It would catch a secret in a
commit that predates the scanner, which is a new guarantee and belongs in
its own decision with its own verification.

## Consequences

- No CI run produces a scan step that reports zero commits.
- A secret already committed before gitleaks existed is still not caught.
  Nothing regressed — that was never covered — but it is now written down.
- **This is coupled to the merge strategy.** The push scan was empty only
  because `main` is merge-commits-only. Squash merging would fill
  `main`'s first-parent line with real commits and a push scan would
  begin working on its own. Anyone changing the merge strategy should
  revisit the `if:` condition and the comment above it, and consider
  whether the duplicate scan is worth its runtime.
- Revisit if Skyline moves under a GitHub Organization, which also
  requires `GITLEAKS_LICENSE`.
