# Vendored skills

These are not Skyline's. They are a copy of [ponytail][upstream] (MIT),
the coding standard `CLAUDE.md` requires, checked in so that every session
and every contributor gets it rather than only whoever installed it.

| Path | Upstream path |
|---|---|
| `ponytail/SKILL.md` | `skills/ponytail/SKILL.md` |
| `ponytail-review/SKILL.md` | `skills/ponytail-review/SKILL.md` |
| `ponytail-audit/SKILL.md` | `skills/ponytail-audit/SKILL.md` |
| `ponytail-debt/SKILL.md` | `skills/ponytail-debt/SKILL.md` |

Copied verbatim from `e3ba2aa6f1e6f0bc4d69eb09c9f0d0a93af56156`. Nothing is
edited locally — a local edit would make the next re-sync a merge, and the
point of a standard is that it is the same one everybody else is reading.

`ponytail/LICENSE` is upstream's MIT licence and covers all four
directories; they are one project.

## Why a copy and not the plugin

Upstream ships ponytail as a Claude Code plugin. A plugin installed on one
machine does not follow you into a remote session's container, so web
sessions ran without it and applied the ladder from memory. A project skill
is in the checkout, so it is there wherever the checkout is.

## Re-syncing

```
for s in ponytail ponytail-review ponytail-audit ponytail-debt; do
  curl -sS -o ".claude/skills/$s/SKILL.md" \
    "https://raw.githubusercontent.com/DietrichGebert/ponytail/main/skills/$s/SKILL.md"
done
```

Then update the revision above to whatever `git ls-remote
https://github.com/DietrichGebert/ponytail HEAD` reports, and read the diff
before committing. `ponytail-gain` and `ponytail-help` are deliberately not
here: a benchmark scoreboard and a command reference do nothing for this
repository.

[upstream]: https://github.com/DietrichGebert/ponytail
