# 5. Python/FastAPI backend with a Svelte frontend

- **Status:** Accepted
- **Date:** 2026-09-20

## Context

Given a web application (ADR-4), the language choice was open. The deciding
factor was the integration surface: Google Calendar, CalDAV, other web
APIs, and Home Assistant over the LAN — plus a hard 1GB memory ceiling
(ADR-6) and the fact that the project is built by a single agent rather
than a team.

## Decision

**Backend: Python 3.11+ with FastAPI.** **Frontend: Svelte.** **Storage:
SQLite in WAL mode.**

## Rationale

Python wins on the integration surface, which is where this application's
real difficulty lives:

- **Recurrence rules.** `dateutil.rrule`, `icalendar`, and
  `recurring-ical-events` handle DST transitions, `EXDATE`, and
  `RECURRENCE-ID` overrides on single instances of a series. This is the
  hardest part of any calendar application and the JavaScript equivalents
  are thinner.
- **CalDAV.** Python's `caldav` is mature; Node's `tsdav` is not
  comparable.
- **Home Assistant is Python.** Its API is language-agnostic, but every
  example, document, and community answer is Python — and shipping Skyline
  as an HA custom component later would require it.
- **Timezones.** `zoneinfo` is in the standard library.

The strongest argument for TypeScript end-to-end was shared types across
the wire. FastAPI generates OpenAPI, from which TypeScript types can be
generated — most of that benefit, kept.

Svelte follows from the memory ceiling: the smallest runtime and smallest
bundles of the candidates. React's larger ecosystem was its main advantage,
and that argument weakened considerably given a single implementer who does
not need familiar components.

## Consequences

- Two languages and two toolchains in CI.
- Dependency choices are constrained by memory: `google-auth` + `httpx`
  rather than `google-api-python-client`; `aiosqlite` rather than an ORM.
- Fewer off-the-shelf Svelte components for calendars and touch gestures,
  so more is built from scratch.
- SQLite on SD card demands care — see ADR-6.
