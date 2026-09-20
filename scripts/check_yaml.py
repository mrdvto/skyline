#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Parse every YAML file in the repository.

actionlint understands workflows, but nothing else here is a workflow.
This covers the rest: `.yaml` as well as `.yml`, and files outside
`.github/`, which is where a compose file or a device config will land.
"""

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

paths = sorted(
    path
    for pattern in ("*.yml", "*.yaml")
    for path in ROOT.rglob(pattern)
    if ".git" not in path.relative_to(ROOT).parts
)

bad = 0
for path in paths:
    try:
        yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        print(f"error: {path.relative_to(ROOT)}: {exc}", file=sys.stderr)
        bad += 1

print(f"{'FAIL' if bad else 'ok'}: {len(paths)} file(s), {bad} invalid")
sys.exit(1 if bad else 0)
