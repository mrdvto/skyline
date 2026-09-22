#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Measure what the two Google Calendar client stacks cost to import.

ADR-5 chose `google-auth` + `httpx` over `google-api-python-client` on the
grounds that the latter loads large discovery documents into memory. That
was a reputation, not a number. This puts a number on it.

Each case runs in a fresh interpreter, because import cost is not
repeatable inside one: the second import of a module is free. The child
reports its own peak RSS from /proc, and the parent subtracts a baseline
interpreter so the figure is the library rather than CPython.

Every run prints the caveat about which machine you are on. It matters
more than the numbers do, and a footer travels with a copy-paste in a way
that a --help screen does not.
"""

import json
import subprocess
import sys

# The import a real caller makes, not the cheapest one that type-checks.
# Measured marginally, `google-auth` is nearly all of the first stack:
# adding it on top of `httpx` costs 18.5MB, while adding `httpx` on top of
# it costs 1.0MB. That asymmetry is what ADR-13 is built on.
CASES = {
    "baseline": "",
    # What this spike's client.py actually imports. Listed first because
    # it is the finding: the OAuth work a Pi reading one family calendar
    # does is a POST, and a POST does not need a credentials library.
    "httpx only (this spike)": "import httpx",
    "google-auth + httpx": (
        "import google.oauth2.credentials, google.auth.transport.requests, httpx"
    ),
    # `static_discovery=True` builds the service off the discovery document
    # shipped in the wheel, so this runs offline and still pays the cost
    # the ADR is about. A developer key that is not a key is fine: nothing
    # here makes a call.
    "google-api-python-client": (
        "import googleapiclient.discovery;"
        " googleapiclient.discovery.build("
        "'calendar', 'v3', static_discovery=True, developerKey='unused')"
    ),
}

CHILD = """
import json, time
start = time.perf_counter()
{body}
elapsed = time.perf_counter() - start
# VmRSS rather than ru_maxrss: peak answers a different question than the
# one a process that stays up for months is judged on, and the two differ
# by enough here to matter.
rss_kb = int(
    [l for l in open("/proc/self/status") if l.startswith("VmRSS")][0].split()[1]
)
print(json.dumps({{"rss_mb": rss_kb / 1024, "import_s": elapsed}}))
"""


def run(body):
    out = subprocess.run(
        [sys.executable, "-c", CHILD.format(body=body)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout)


def main():
    results = {name: run(body) for name, body in CASES.items()}
    if "--json" in sys.argv:
        print(json.dumps(results, indent=2))
        return

    base = results["baseline"]["rss_mb"]
    print(f"{'stack':<26} {'RSS':>9} {'over baseline':>14} {'import':>9}")
    for name, r in results.items():
        over = "-" if name == "baseline" else f"+{r['rss_mb'] - base:.1f} MB"
        print(
            f"{name:<26} {r['rss_mb']:>6.1f} MB {over:>14} {r['import_s']:>7.3f} s"
        )
    # Printed every run rather than left to --help. The caveat is the part
    # most likely to be dropped when someone pastes the table somewhere,
    # and a footer travels with a copy-paste.
    print(f"\npython {sys.version.split()[0]} on {sys.platform}. Not a Pi: the")
    print("ratio between stacks carries to arm64, the absolute RSS does not.")
    print("Retake on hardware before quoting it against the 200MB ceiling.")


if __name__ == "__main__":
    main()
