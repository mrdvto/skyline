# 8. The backend host is a deployment choice; the Pi stays the floor

- **Status:** Accepted
- **Date:** 2026-09-21

## Context

[ADR-6](0006-1gb-pi4-hardware-floor.md) makes the 1GB Pi 4 the supported
floor and gives the backend 200MB of it. That was written assuming the
backend runs on the Pi.

The maintainer has a NAS with RAID. Running the backend there would give
the backend more memory than the whole Pi has, move the database off an SD
card onto redundant storage, and free the Pi's entire backend budget for
Chromium, which [ADR-4](0004-web-app-in-kiosk-browser.md) identifies as
the largest consumer.

Three things were considered and rejected outright.

Putting the live SQLite database on a network share does not work. WAL
mode needs shared-memory locking, which does not exist over NFS or SMB.
There is a single-connection `locking_mode=EXCLUSIVE` escape hatch, and
building on it would be a bad trade. It would also make every screen
depend on the NAS being up, which contradicts the offline-first rule.

Making the NAS the primary host would require a new machine to run a
family wall calendar. Skyline is AGPL software intended for other people
to run, and most of them do not have a NAS.

Keeping the Pi as the only supported host leaves the NAS's reliability
unused for no reason.

## Decision

The backend makes no assumption about its host.

The **Pi-hosted topology is the supported floor**. ADR-6's budget, and
the discipline that comes with it, is unchanged.

The **NAS-hosted topology is a documented alternative**: the backend and
database in a container on the NAS, the Pi reduced to a kiosk browser.

What this requires of the design: no localhost-only assumptions, the
database path and bind address in configuration, and the frontend
reaching the backend by URL rather than by assuming it is local.

Packaging follows the host. The Pi gets an install script and systemd
units, with no Docker, because the daemon alone would take most of the
90MB of headroom. The NAS gets a published container image, because that
is how anything runs on a NAS.

The live database is never on a network share in either topology. The NAS
is a backup destination and, later, a CalDAV origin.

## Consequences

- ADR-6 still binds. Development happens against the floor, so the
  constraint stays visible rather than being discovered at release.
- Two deployment paths to document and test. Both run the same process
  with different configuration, so the divergence is small.
- Households without a NAS are unaffected, which keeps the project
  installable by its stated audience.
- The NAS becomes load-bearing for anyone who chooses that topology. That
  is their trade to make, and it is written down.
