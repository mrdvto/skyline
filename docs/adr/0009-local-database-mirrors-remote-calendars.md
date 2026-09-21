# 9. The local database mirrors remote calendars, and the remote wins

- **Status:** Accepted
- **Date:** 2026-09-21

## Context

Skyline keeps calendar data in SQLite and syncs against Google Calendar
and CalDAV. Whether that local copy is authoritative decides the data
model, the conflict rules, and how hard the sync engine is.

The fact that settles it: the family's calendars are all in Google
Calendar today, and they are edited on phones throughout the day. Skyline
is usually the second writer, not the first.

Three models were considered.

Treating the local database as the system of record and pushing outward
is clean to describe and wrong in practice. Every edit made on a phone in
Google Calendar would be racing Skyline, and losing.

True bidirectional field-level merge, with causality tracking and no
designated winner, is the theoretically correct answer. It is also where
calendar projects go to die, because recurrence overrides and merge
interact badly. `RECURRENCE-ID` exceptions, `EXDATE`, and a series edited
on both sides produce cases with no defensible automatic answer.

## Decision

Every calendar carries an origin: `google:<id>`, `caldav:<url>`, or
`local`.

For remote origins the local database is a **mirror**, and the **remote
wins** any conflict. A local edit is recorded as a pending change, sent
to the remote, and the authoritative result arrives on the next pull. The
screen shows the change optimistically in the meantime, marked pending.

For `local` origin, events exist only in SQLite and never sync. No
conflict is possible.

CalDAV writes are conditional on the stored `ETag`. A `412` means the
remote changed first: re-pull, discard the local change, record it.

## Consequences

- The conflict rule is one sentence per origin, and it matches where the
  family actually edits.
- Skyline works with no Google account at all, using `local` calendars.
- Migrating to a self-hosted CalDAV server later is adding an origin, not
  changing the model.
- A local edit can be silently overwritten by a concurrent remote edit.
  That is the accepted cost of not building merge. The pending marker and
  the sync status indicator make the window visible rather than hidden.
- Pending changes are durable rows, so an edit made while the WAN is down
  is replayed when it returns rather than lost.
