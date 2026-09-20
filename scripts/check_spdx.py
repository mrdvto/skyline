#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Check that every source file carries the SPDX licence header.

CLAUDE.md and CONTRIBUTING.md both require
`SPDX-License-Identifier: AGPL-3.0-or-later` at the top of every source
file, and the PR template asks for it on the honour system. This is the
part that can fail.

The licence is the point of an AGPL project. A file that ships without a
header is one a downstream reader cannot tell the licence of, and the
header is the only place that answer travels with the file.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPDX = "SPDX-License-Identifier: AGPL-3.0-or-later"

# Checked. Everything here has comment syntax and is source in the sense
# that matters: someone could copy the file out of the repository on its
# own and need to know its licence.
REQUIRED = (".py", ".sh", ".js", ".ts", ".svelte", ".yml", ".yaml", ".toml")

# Not checked, and the reasons are here rather than implied by absence:
#
#   .json           no comment syntax. A sidecar or a smuggled key would
#                   be machinery for one settings file; REUSE solves this
#                   properly if it ever earns its place (see issue #11).
#   .gitignore      config for git, not source. They accept `#`, so this
#   .gitattributes  is a choice, not a limitation.
#   .md             prose. The repository licence covers it, and a header
#                   on top of a README reads as noise.
#   LICENSE         is the licence.
#
# Anything with a suffix outside REQUIRED is out of scope by construction;
# adding a language means adding it above deliberately.

# The header has to be at the top, but not on line 1: a shebang, an
# encoding line, or a blank line can come first.
HEAD_LINES = 5


def tracked_files():
    """Tracked files only -- git already knows what belongs to the project.

    Walking the tree instead would mean maintaining a skip list for .git,
    __pycache__, node_modules and a virtualenv. If git cannot answer, the
    check fails rather than passing on an empty list: a check that gates
    nothing is worse than no check.

    The cost is that a brand new file is invisible until it is staged. CI
    sees every file in the PR, so this only bites a local run made before
    `git add`.
    """
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return sorted(ROOT / name for name in out.split("\0") if name)


try:
    paths = [p for p in tracked_files() if p.suffix in REQUIRED]
except (subprocess.CalledProcessError, FileNotFoundError) as exc:
    print(f"error: cannot list tracked files: {exc}", file=sys.stderr)
    sys.exit(1)

missing = []
for path in paths:
    with path.open(encoding="utf-8") as handle:
        head = [line for _, line in zip(range(HEAD_LINES), handle)]
    if not any(SPDX in line for line in head):
        missing.append(path.relative_to(ROOT))

for path in missing:
    print(f"error: {path}: no '{SPDX}' in the first {HEAD_LINES} lines", file=sys.stderr)
print(f"{'FAIL' if missing else 'ok'}: {len(paths)} file(s), {len(missing)} missing")
sys.exit(1 if missing else 0)
