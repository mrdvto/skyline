#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Check that the ADR set is coherent and that relative doc links resolve.

The ADRs are the only durable record of why Skyline is built the way it is,
so a gap in the numbering or a link that rots is a real defect, not a typo.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADR_DIR = ROOT / "docs" / "adr"
ADR_NAME = re.compile(r"^(\d{4})-[a-z0-9-]+\.md$")
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

errors = []


def check_adrs():
    files = sorted(p for p in ADR_DIR.glob("*.md"))
    if not files:
        errors.append(f"{ADR_DIR}: no ADRs found")
        return

    seen = []
    for path in files:
        match = ADR_NAME.match(path.name)
        if not match:
            errors.append(f"{path.name}: expected NNNN-lower-case-slug.md")
            continue

        number = int(match.group(1))
        seen.append(number)
        text = path.read_text(encoding="utf-8")

        heading = re.match(r"^# (\d+)\. .+", text)
        if not heading:
            errors.append(f"{path.name}: first line must be '# N. Title'")
        elif int(heading.group(1)) != number:
            errors.append(
                f"{path.name}: heading says {heading.group(1)}, filename says {number}"
            )

        for field in ("**Status:**", "**Date:**"):
            if field not in text:
                errors.append(f"{path.name}: missing {field}")

    expected = list(range(1, len(seen) + 1))
    if sorted(seen) != expected:
        errors.append(f"ADR numbering is not contiguous from 1: {sorted(seen)}")


def check_links():
    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts:
            continue
        for target in LINK.findall(path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            resolved = (path.parent / target.split("#", 1)[0]).resolve()
            if not resolved.exists():
                rel = path.relative_to(ROOT)
                errors.append(f"{rel}: broken link -> {target}")


check_adrs()
check_links()

for error in errors:
    print(f"error: {error}", file=sys.stderr)
print(f"{'FAIL' if errors else 'ok'}: {len(errors)} problem(s)")
sys.exit(1 if errors else 0)
