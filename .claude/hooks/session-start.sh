#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Orients a fresh session: where the branch stands, whether it needs
# restarting, and what is uncommitted. Sessions share no memory, so this is
# the only thing that reliably tells one where it woke up.
#
# Prints and exits 0 no matter what. A broken hook must never block a
# session, so every git call here is allowed to fail quietly.

set -uo pipefail

cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || echo .)}" || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

DEFAULT_BRANCH=main

# Prunes refs for branches deleted on merge. Without this, stale refs make
# a branch look ahead of a remote that no longer exists, which is what made
# the stop hook report phantom unpushed commits.
#
# No refspec, deliberately. Passing one ("origin main") limits pruning to
# refs matching it, so refs for deleted branches survive and the bug this
# is here to prevent still happens.
git fetch --prune --quiet origin 2>/dev/null

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
echo "Skyline — branch: $branch"

if git rev-parse --verify --quiet "origin/$DEFAULT_BRANCH" >/dev/null 2>&1; then
  ahead=$(git rev-list --count "origin/$DEFAULT_BRANCH..HEAD" 2>/dev/null || echo 0)
  behind=$(git rev-list --count "HEAD..origin/$DEFAULT_BRANCH" 2>/dev/null || echo 0)

  if [ "$branch" = "$DEFAULT_BRANCH" ]; then
    echo "  on $DEFAULT_BRANCH — branch before committing (direct pushes are blocked)"
  elif [ "$ahead" -eq 0 ] && [ "$behind" -gt 0 ]; then
    echo "  RESTART NEEDED: no unmerged commits, $behind behind $DEFAULT_BRANCH."
    echo "  Its PR is merged. Do not stack new work here. Restart the branch:"
    echo "    git fetch origin $DEFAULT_BRANCH && git checkout -B $branch origin/$DEFAULT_BRANCH"
  elif [ "$ahead" -gt 0 ]; then
    echo "  $ahead unmerged commit(s), $behind behind $DEFAULT_BRANCH"
    [ "$behind" -gt 0 ] && echo "  merge $DEFAULT_BRANCH in before pushing further"
  else
    echo "  even with $DEFAULT_BRANCH — clean start"
  fi
fi

dirty=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
[ "$dirty" -gt 0 ] && echo "  $dirty uncommitted change(s) — inspect before assuming they are yours"

# A local branch with no upstream has no PR, so nothing records why it
# exists. That is the orphan CLAUDE.md is written to prevent.
orphans=$(git for-each-ref --format='%(refname:short) %(upstream)' refs/heads 2>/dev/null \
  | awk -v def="$DEFAULT_BRANCH" '$2 == "" && $1 != def {print "    " $1}')
if [ -n "$orphans" ]; then
  echo "  local branches with no upstream (no PR, no recorded reason):"
  echo "$orphans"
fi

cat <<'NOTES'

  Constraints: 1GB Pi 4 floor · AGPL-3.0-or-later · offline-first
  Workflow: issue -> branch -> draft PR on FIRST push. Claude does not merge.
  Open PRs and issues are not listed here; check them with the GitHub tools.
NOTES

exit 0
