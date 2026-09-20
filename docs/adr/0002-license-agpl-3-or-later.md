# 2. License under AGPL-3.0-or-later

- **Status:** Accepted
- **Date:** 2026-09-20

## Context

The repository was initialized with GPL-3.0. Skyline is expected to grow a
server component — calendar sync, Home Assistant integration, and remote
access from family phones.

GPLv3 triggers its source obligations on *distribution*. Someone who forks
Skyline, improves it, and offers it as a hosted service never distributes a
copy, so they owe nothing back. AGPLv3 §13 closes this: users interacting
with a modified version over a network must be offered its source.

The choice is effectively permanent. While the project has a single
copyright holder it can be relicensed freely; once outside contributions
land, relicensing requires every contributor's consent.

## Decision

Skyline is licensed **AGPL-3.0-or-later**.

Every source file carries `SPDX-License-Identifier: AGPL-3.0-or-later`.

Dependencies under GPLv2-only or proprietary licenses are incompatible and
will not be used.

## Consequences

- Hosting a modified Skyline requires publishing the modifications.
- No cost to the intended user: running it on your own Pi for your own
  family is not distribution and triggers nothing.
- Some organizations forbid AGPL software by policy, which may deter a
  few contributors. Judged acceptable — the contributor pool for a
  self-hosted family dashboard is hobbyists, not corporate teams.
- `-or-later` allows adopting future FSF revisions without tracking down
  contributors. It does **not** permit moving to a different license.
- AGPL code cannot later be absorbed into a GPL-only project. One-way door,
  entered deliberately.
