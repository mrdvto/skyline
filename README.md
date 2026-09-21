# Skyline

Family organization for the kitchen wall — shared calendar, to-dos, and
household coordination on a Raspberry Pi with a touch monitor.

Self-hosted. Offline-first. Free software.

> **Status: early development.** Nothing is installable yet. The
> architecture is settled in [`docs/adr/`](docs/adr/) and the v1.0 design
> is written down in [`docs/sdd.md`](docs/sdd.md); the first vertical
> slice is being built.

## What it is

A Raspberry Pi mounted behind a touchscreen, booting straight into Skyline.
The whole family sees the same calendar and task list, touches it to make
changes, and never has to open an app to find out who's picking up whom.

Because Skyline is a web application served from the Pi, phones and
tablets on the network reach it with no extra install. In v1.0 they can
read the calendar and add events quickly; the wall screen is where
everything else happens.

## Planned capabilities

- Shared family calendar with two-way Google Calendar and CalDAV sync
- Shared and per-person to-do lists
- Home Assistant integration for household state
- Full function with no internet connection; sync reconciles when it returns

## Design constraints

Skyline targets the **1GB Raspberry Pi 4** as its hardware floor — not as a
minimum it limps along on, but as a machine it runs well on. That shapes
everything: lean dependencies, a tracked memory budget, and no reliance on
swap. See [ADR-6](docs/adr/0006-1gb-pi4-hardware-floor.md).

| | |
|---|---|
| Backend | Python 3.11+ / FastAPI |
| Frontend | Svelte |
| Storage | SQLite (WAL) |
| Display | Chromium kiosk on Raspberry Pi OS Lite |
| Hardware floor | Raspberry Pi 4, 1GB RAM |

## Documentation

- [Software design document](docs/sdd.md) — how Skyline works
- [Architecture decisions](docs/adr/) — what was chosen, and why
- [CONTRIBUTING.md](CONTRIBUTING.md) — workflow and standards
- [CLAUDE.md](CLAUDE.md) — operating guide for AI-assisted development
- [SECURITY.md](SECURITY.md) — how to report a vulnerability privately
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — Contributor Covenant 3.0

## License

Copyright (C) 2026 David Vuong

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public
License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

**In plain terms:** run it, modify it, share it. If you host a modified
version where others use it over a network, you must share your changes
too. Running Skyline on your own Pi for your own family triggers no
obligations at all.
