# Skyline software design document

- **Version:** 1.0 (draft)
- **Date:** 2026-09-21
- **Status:** Living document. Revised as the design changes.

This describes how Skyline works. The [ADRs](adr/) record decisions that
are expensive to reverse, with the alternatives rejected and why. Where
the two overlap, this document states the decision in a line and links
the ADR rather than re-arguing it.

Nothing here is built yet. This is the design the first code implements.

## 1. What Skyline is

A Raspberry Pi behind a touchscreen on a kitchen wall, showing one family
calendar and one chore list, served by a backend on the same device.

The family already has calendars. They are in Google Calendar, edited on
phones, all day. Skyline does not replace that and does not try to. It is
the shared surface in the room where the family actually coordinates, and
it keeps working when the internet does not.

### 1.1 In scope for v1.0

- Shared calendar, two-way sync with Google Calendar and CalDAV
- To-do lists, shared and per-person, with recurring chores
- A weather panel
- A portrait kiosk on the wall
- A responsive phone view limited to reading and quick-add

### 1.2 Out of scope for v1.0

| Deferred | Why |
|---|---|
| Home Assistant | A third sync source and a second auth model. It is an add-on, not a pillar, and the first thing to cut if the 200MB backend ceiling gets tight. Planned for v1.1. |
| To-do sync to any remote | Chores get ticked off at the wall. Google Tasks is a separate API with a thinner model; CalDAV `VTODO` support across servers is uneven. The schema leaves room. |
| Off-LAN access | Requires real authentication, which retires the profile model in §8. |
| Push notifications | Needs HTTPS, which v1.0 does not require. See [ADR-11](adr/0011-http-by-default-https-optional.md). |
| Phone parity (settings, calendar management, onboarding) | Kiosk-only in v1.0. Phones get read and quick-add. |
| A full design system | v1.0 ships tokens, not a system. See §12. |

## 2. Constraints

From [ADR-6](adr/0006-1gb-pi4-hardware-floor.md): 1GB Pi 4, 200MB for the
backend, no swap to the SD card, RSS is a tracked metric.

From [ADR-2](adr/0002-license-agpl-3-or-later.md): AGPL-3.0-or-later, so
no GPLv2-only or proprietary dependencies.

From [ADR-5](adr/0005-python-fastapi-and-svelte.md): Python 3.11+,
FastAPI, Svelte, SQLite in WAL mode, `aiosqlite` rather than an ORM,
`google-auth` plus `httpx` rather than `google-api-python-client`.

Two consequences bind most of what follows. The backend is one process,
because a second Python interpreter costs 30 to 50MB of a 200MB budget
before it does anything. And no screen may wait on a remote call, because
the WAN is allowed to be down.

## 3. Architecture

```
 Raspberry Pi 4 (1GB)                              WAN
+-------------------------------------+        +------------------+
|  Chromium kiosk (portrait)          |        | Google Calendar  |
|      |                              |   +--->| CalDAV server    |
|      | HTTP + SSE                   |   |    | Open-Meteo       |
|      v                              |   |    +------------------+
|  uvicorn : FastAPI (one process)    |   |
|      |         |                    |   |
|      |         +- sync tasks -------+---+
|      |         +- weather task      |
|      |         +- backup task ------+---> NAS (SMB/NFS)
|      v                              |
|  SQLite (WAL, synchronous=FULL)     |
|  /var/lib/skyline/skyline.db        |
+-------------------------------------+
        ^
        | HTTP over LAN
   family phones (read + quick-add)
```

Every read served to a screen comes from SQLite. Background tasks
reconcile SQLite against remote sources. Nothing in the request path
touches the network.

### 3.1 Process model

One `uvicorn` process, one worker. Sync loops, the weather refresh, and
the backup job are `asyncio` tasks started in the FastAPI lifespan
handler. Database access goes through `aiosqlite`.

Each background task runs inside a supervisor wrapper that catches
exceptions, records them against the origin, and restarts the task with
exponential backoff. A wedged sync must not take the API down with it.

Recurrence expansion is CPU work on the event loop. It stays bounded by
expanding only the requested window, never an open-ended range. If a
window expansion is ever measured above a few milliseconds, it moves to a
thread via `asyncio.to_thread` rather than growing a second process.

### 3.2 Deployment topologies

Two supported shapes, one codebase. See
[ADR-8](adr/0008-deployment-flexible-backend-host.md).

**Pi-hosted (the supported floor).** Backend and database on the Pi.
Installed by a bootstrap script: service user, virtualenv,
`/var/lib/skyline`, systemd units. Updates are `git pull`, `pip install`,
`systemctl restart`, wrapped in one script. No Docker on the Pi; the
daemon alone would take most of the 90MB headroom.

**NAS-hosted (documented alternative).** Backend and database in a
container on a NAS, the Pi reduced to a kiosk browser. Better durability,
more headroom, and the whole backend budget freed for Chromium. Costs a
second always-on machine.

The backend makes no assumption about its host. Database path, bind
address, and the frontend's API base URL are all configuration. The
frontend reaches the backend by URL either way.

## 4. Data model

SQLite, WAL mode, `synchronous=FULL`. Schema in `db/schema.sql`,
migrations in `db/migrations/`.

### 4.1 Origins

Every calendar has an origin, and the origin determines who wins a
conflict. See [ADR-9](adr/0009-local-database-mirrors-remote-calendars.md).

| Origin | Meaning | Conflict rule |
|---|---|---|
| `google:<calendar_id>` | Mirror of a Google calendar | Remote wins |
| `caldav:<collection_url>` | Mirror of a CalDAV collection | Remote wins |
| `local` | Exists only in Skyline | No conflict possible |

A local edit to a mirrored event is not applied to the local row and then
pushed. It is recorded as a pending change, sent to the remote, and the
authoritative result comes back on the next pull. The screen shows the
change optimistically in the meantime, marked pending.

### 4.2 Tables

```sql
CREATE TABLE person (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    color        TEXT NOT NULL,        -- token name, not a hex value
    sort_order   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE calendar (
    id           INTEGER PRIMARY KEY,
    origin       TEXT NOT NULL,        -- 'google:<id>' | 'caldav:<url>' | 'local'
    name         TEXT NOT NULL,
    color        TEXT NOT NULL,
    enabled      INTEGER NOT NULL DEFAULT 1,
    sync_token   TEXT,                 -- Google syncToken / CalDAV sync-token
    last_success TEXT,                 -- ISO 8601 UTC
    last_error   TEXT,
    UNIQUE (origin)
);

CREATE TABLE event (
    id            INTEGER PRIMARY KEY,
    calendar_id   INTEGER NOT NULL REFERENCES calendar(id) ON DELETE CASCADE,
    remote_uid    TEXT,                -- iCalendar UID; NULL for local-origin
    etag          TEXT,                -- for conditional CalDAV writes
    summary       TEXT NOT NULL,
    description   TEXT,
    location      TEXT,
    -- Timed events: UTC instant plus the zone the rule expands in.
    -- All-day events: start_date/end_date set, start_utc/end_utc NULL.
    start_utc     TEXT,
    end_utc       TEXT,
    start_date    TEXT,
    end_date      TEXT,
    tzid          TEXT,
    rrule         TEXT,
    exdate        TEXT,                -- comma-separated
    recurrence_id TEXT,                -- set on override rows
    series_id     INTEGER REFERENCES event(id) ON DELETE CASCADE,
    person_id     INTEGER REFERENCES person(id) ON DELETE SET NULL,
    updated_at    TEXT NOT NULL,
    UNIQUE (calendar_id, remote_uid, recurrence_id)
);

CREATE INDEX event_range ON event (calendar_id, start_utc, end_utc);
CREATE INDEX event_date_range ON event (calendar_id, start_date, end_date);

CREATE TABLE task (
    id           INTEGER PRIMARY KEY,
    title        TEXT NOT NULL,
    notes        TEXT,
    person_id    INTEGER REFERENCES person(id) ON DELETE SET NULL,
    due_date     TEXT,                 -- next due occurrence, or one-off due date
    rrule        TEXT,                 -- NULL for a one-off task
    tzid         TEXT,
    archived_at  TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

CREATE TABLE task_completion (
    id              INTEGER PRIMARY KEY,
    task_id         INTEGER NOT NULL REFERENCES task(id) ON DELETE CASCADE,
    occurrence_date TEXT NOT NULL,
    person_id       INTEGER REFERENCES person(id) ON DELETE SET NULL,
    completed_at    TEXT NOT NULL,
    UNIQUE (task_id, occurrence_date)
);

CREATE TABLE pending_change (
    id           INTEGER PRIMARY KEY,
    calendar_id  INTEGER NOT NULL REFERENCES calendar(id) ON DELETE CASCADE,
    event_id     INTEGER REFERENCES event(id) ON DELETE CASCADE,
    operation    TEXT NOT NULL,        -- 'create' | 'update' | 'delete'
    payload      TEXT NOT NULL,        -- JSON
    attempts     INTEGER NOT NULL DEFAULT 0,
    last_error   TEXT,
    created_at   TEXT NOT NULL
);

CREATE TABLE setting (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);

CREATE TABLE weather_cache (
    fetched_at TEXT PRIMARY KEY,
    payload    TEXT NOT NULL
);
```

### 4.3 Time

Timed events store a UTC instant and the originating `TZID`. Both are
needed: the instant for range queries, the zone because an `RRULE` has to
expand in its own zone to survive a DST transition.

All-day events store `start_date` and `end_date` as dates, never a
midnight timestamp. Storing an all-day event as midnight in some zone is
the bug that moves birthdays a day when the zone changes.

Display uses a single household timezone from `setting`, not the
browser's. v1.0 is kiosk-first, and a wall screen and a phone showing
different times for the same event reads as a bug to anyone who is not a
programmer.

`zoneinfo` handles all of it. Standard library, no dependency.

### 4.4 Recurrence

A series is one row carrying `DTSTART`, `RRULE`, and `EXDATE`. Overrides
to single instances are separate rows with `recurrence_id` set and
`series_id` pointing at the master.

Instances are never materialised. A range query expands the series that
could overlap the range, using `dateutil.rrule`, and returns the
instances. A daily standup running since 2019 stays one row, editing the
series is one write, and nothing needs re-expanding in the background.

The cost is CPU per range query. At a family's volume that is nothing. If
it ever stops being nothing, the fix is a cache, and a cache is easier to
add later than a materialisation horizon is to remove.

### 4.5 Recurring chores

Tasks reuse the same `RRULE` machinery. `due_date` holds the next
occurrence. Completing a chore writes a `task_completion` row for that
occurrence and advances `due_date` to the next one.

The completion log is what makes "has anyone fed the cat today" answerable
after the fact, which on a shared screen is asked constantly.

## 5. Sync engine

### 5.1 Cadence

A 5-minute tick per enabled calendar. Exponential backoff while the WAN
is unreachable, capped at 30 minutes. Local writes push immediately
rather than waiting for the tick.

Push channels would be better than polling, and they need a public HTTPS
webhook URL, which v1.0 does not have.

### 5.2 Google

`google-auth` for tokens, `httpx` against the REST endpoints directly.
`google-api-python-client` is not used.

This section used to justify that by saying `google-api-python-client` loads
large discovery documents into memory. The spike for #29 measured it: the
Calendar discovery document costs 0.61MB and the two stacks are within 0.1MB
of each other, so the justification was false and is removed rather than
reworded. [ADR-13](adr/0013-google-calendar-authorization-flow.md) has the
numbers and the reasons that do hold. It also proposes dropping `google-auth`,
which would rewrite the first line above; that waits on the ADR being
accepted.

Pull is `events.list` with the stored `syncToken`, so only deltas cross
the wire. A `410 Gone` means the token expired: discard it and do a full
resync of that calendar.

Push is `events.insert` / `patch` / `delete` from the `pending_change`
queue. A change that fails is retried with backoff; after a threshold it
is surfaced against the origin and left in the queue for a human.

### 5.3 CalDAV

The `caldav` library. Pull uses the `sync-collection` REPORT of RFC 6578
when the server advertises it, falling back to comparing the collection
`CTag` and then per-resource `ETag`s.

Push uses conditional PUT with `If-Match` on the stored `ETag`. A 412
means the remote changed underneath us: re-pull that resource, discard
the local change, and record it. Remote wins, per §4.1.

### 5.4 Credentials

Every household registers its own Google Cloud OAuth client. The
repository cannot ship a client ID and secret: that violates the secrets
rule in `CLAUDE.md`, and a credential published in a public repository is
revoked anyway. This is real onboarding friction and it is not avoidable.

Consent uses the installed-app loopback flow with a `127.0.0.1` redirect,
which is the only redirect Google permits without a public HTTPS URL. It
is completed in the kiosk's own browser, or through an SSH tunnel from a
laptop, which is much kinder than typing a Google password on a
touchscreen.

CalDAV uses an app password per account.

Both live in `/var/lib/skyline/credentials.json`, mode 0600, owned by the
service user, outside the repository. This is filesystem permissions, not
encryption. Anyone holding the SD card holds the tokens. Encrypting them
on a Pi with no TPM and an unattended boot would put the key on the same
disk, which stops an idle reader and nothing else.

See §17 for the device-flow question, which is open.

### 5.5 Weather

Open-Meteo, no API key, so there is no credential to store and no signup
step for anyone running Skyline. One `httpx` call, cached in
`weather_cache`. When the WAN is down the panel shows the cached reading
with its timestamp. The provider sits behind one module so swapping it is
a small change.

## 6. API

REST for writes, Server-Sent Events for change notification.

SSE is plain HTTP, reconnects on its own in every browser, and needs no
library on either side. One long-lived text connection per device costs
almost nothing at family scale. A WebSocket would add a protocol and a
heartbeat implementation to buy bidirectionality that nothing needs.

```
GET    /api/events?from=&to=          expanded instances in a window
POST   /api/events
PATCH  /api/events/{id}
DELETE /api/events/{id}               ?scope=instance|series

GET    /api/tasks?due_before=
POST   /api/tasks
PATCH  /api/tasks/{id}
POST   /api/tasks/{id}/complete       body: occurrence_date, person_id
DELETE /api/tasks/{id}/complete/{occurrence_date}

GET    /api/people
GET    /api/calendars
PATCH  /api/calendars/{id}            enable, disable, recolour

GET    /api/weather
GET    /api/settings
PATCH  /api/settings

GET    /api/health                    version, uptime, per-origin sync
                                      state, DB size, RSS
GET    /api/stream                    SSE change feed
```

Change events carry a type and an affected range, not a payload. The
client refetches the range it is displaying. Sending full objects over
SSE would mean maintaining a second serialisation path that can disagree
with the REST one.

FastAPI generates OpenAPI; TypeScript types for the frontend are
generated from it, which recovers most of what an all-TypeScript stack
would have given.

## 7. Frontend

Svelte with Vite, built to static assets, served by FastAPI's
`StaticFiles`. No Node on the Pi at runtime. Building happens in CI or on
a laptop; the Pi only ever receives built files.

Routing is client-side. There are about six routes.

### 7.1 Layout targets

Portrait is the primary target, 600x1024 through 1080x1920. Landscape
works but is second-class. Phones are supported for reading and
quick-add.

A phone is a small portrait kiosk, which is why designing portrait-first
made the responsive work cheap rather than a second application.

### 7.2 Screens

The kiosk shows one dashboard: an agenda-led calendar as the dominant
panel, today's chores beside or below it, weather and clock in a header
strip. Adding and editing happen in sheets over the dashboard, not on
separate pages. After an idle interval the view returns to the dashboard,
so the wall is never left sitting on a sub-screen.

Phones get the same dashboard stacked, plus quick-add. Settings, calendar
management, and OAuth onboarding are kiosk-only in v1.0.

### 7.3 Sync status

A per-origin status indicator is always visible. Green when the last sync
succeeded recently, amber when the data is getting stale, red when
authentication is broken or the origin has failed repeatedly.

The thresholds are tuned so that a healthy household sees green nearly
always. An indicator that sits amber half the time teaches people to
ignore it, which is worse than having none.

The settings screen lists every origin with its last success and its last
error verbatim.

### 7.4 Reminders

Events inside a lead-time window, 30 minutes by default and configurable,
are promoted visually on the wall, and wake the screen if it is blanked.

No push, no email, no sound. Push needs HTTPS, which is optional in v1.0.
This suits how the thing is actually used: people walk past the kitchen
screen.

## 8. Identity, trust, and the write PIN

People are rows in `person`, used for ownership and filtering. They are
not accounts. There are no passwords and no sessions.

The LAN is the trust boundary. See
[ADR-10](adr/0010-lan-trust-boundary-and-write-pin.md).

Reads are open to anything that can reach the Pi. Writes require a
household PIN, sent in a header. A device is enrolled once by entering
the PIN, after which it lives in `localStorage`, so the kiosk and each
family phone are asked exactly once.

What this buys: a guest's phone, a child's tablet, and a smart TV browser
cannot change the family calendar by wandering onto it.

What it does not buy: the PIN crosses the network in the clear, because
v1.0 does not require HTTPS. Someone with the Wi-Fi password who wants to
capture it can. This stops casual and accidental writes, not a determined
person already inside the network.

Because the PIN is short enough to type on a phone and read off the
fridge, write endpoints are rate-limited per client address, and repeated
failures are logged.

What holds regardless of any of this, and is never trimmed: input
validation at the API boundary, no credentials in any response, CORS
restricted to the app's own origin, and no path that exposes Skyline
beyond the LAN.

### 8.1 HTTPS

Optional, documented, not required. See
[ADR-11](adr/0011-http-by-default-https-optional.md).

Two paths work on a LAN: a certificate from Let's Encrypt using the
DNS-01 challenge on a domain you own, with an A record pointing at the
private address, or a NAS reverse proxy that already does the certificate
handling. Self-signed certificates are documented as a poor third,
because installing and trusting them on every family device, and doing it
again at expiry, is hostile.

Turning HTTPS on makes the PIN confidential in transit, and unlocks a
service worker, PWA installation, and Web Push. Those are named as what
it buys so the tradeoff is visible, and they stay out of v1.0 because
requiring a domain to run a family calendar is the wrong bar.

## 9. Kiosk lifecycle and screen power

All of it is systemd units and shell scripts. No application code.

**Renderer restart.** Chromium restarts daily at 04:00. Long-running
kiosk browsers leak, and session state lives on the server, so nothing is
lost. A watchdog also restarts it if RSS crosses a threshold before then,
because a fixed schedule cannot save you from a bad day.

**Quiet hours.** The backlight is switched off, not dimmed, between
configurable hours, 23:00 to 06:30 by default. Backlight control rather
than DPMS: the touch controller stays live, so touch-to-wake is reliable,
and HDMI monitors driven into standby can take seconds to resync and wake
badly.

Most of a panel's power is the backlight rather than the logic board, so
switching it off captures the large majority of the saving that a full
panel power-down would.

**Daytime idle blanking.** Implemented, configurable, and off by default.
An empty house looks exactly like nobody touching the screen, so an idle
timeout captures the daytime saving without any presence detection. It
also makes the wall calendar dark when someone wants to glance at it,
which is the entire point of a wall calendar. The right timeout depends
on how a particular kitchen behaves, so the mechanism ships and the
default does not guess.

**Wake.** Any touch wakes the screen for a configurable interval, then it
blanks again.

Blanking and waking sit behind one small abstraction with two operations,
so a Home Assistant presence signal can drive it in v1.1 without rework.
That is where real presence belongs: Home Assistant already solves it
with the phone app, router integration, and BLE trackers, and it is
already on the roadmap. Building presence detection inside Skyline would
mean either hardware or ARP-based device tracking, and phones sleep their
Wi-Fi and randomise their MAC addresses, so the screen would blank while
someone is standing in front of it.

## 10. Durability and backup

`synchronous=FULL` with WAL. A committed write survives sudden power
loss, at the cost of an fsync per commit, which is irrelevant at a
family's write volume and is the entire reason power loss is in scope.

Nightly `VACUUM INTO` a timestamped file, then copy to a CIFS-mounted NAS
share. `VACUUM INTO` is safe on a live database; `cp` of a WAL-mode
database is not.

Retention is 14 daily and 8 weekly snapshots. An unreachable NAS makes
the backup fail into the status indicator and never blocks the
application.

Restore is a documented procedure, and it is rehearsed. A backup nobody
has restored is not a backup.

## 11. Configuration

Split by who changes it.

`/etc/skyline/config.toml`, or environment variables in the container
topology, holds only what is needed before the database opens: database
path, bind address, log level, credentials path, write PIN, API base URL.

Everything a person would change lives in the `setting` table and is
edited on the settings screen: people, household timezone, weather
location, which calendars sync, quiet hours, idle timeout, reminder lead
time. Nobody should have to SSH in to add a family member.

### 11.1 First run

The kiosk shows a setup flow: household timezone, weather location,
people, the write PIN, then optionally connecting Google or CalDAV.

Skyline is usable with local calendars before any remote is connected.
Connecting Google is a step, not a prerequisite.

## 12. Visual design

v1.0 ships tokens, not a design system. The tokens are CSS custom
properties on `:root`. A proper design system, with a component
inventory and usage rules, is a named v1.1 deliverable, to be written
when phone parity and more screens arrive.

The unusual constraint is viewing distance. A kitchen wall screen is read
from two to three metres, not fifty centimetres. That inverts the normal
type scale, pushes the minimum touch target well above the usual 44px,
and raises the contrast floor. It is the one thing a generic design
system would get wrong.

Tokens cover surface and text colours, an accent, a per-person palette, a
status palette for green, amber, and red, a type scale anchored to
viewing distance, a spacing scale, a minimum touch target, and motion
durations.

### 12.1 Themes

Light by day, dark by night, switched on the same schedule as quiet
hours. Light reads better across a bright kitchen at breakfast; dark
avoids a glowing rectangle in a dark room at midnight.

Every token is a validated pair. The per-person palette has to clear
contrast on both surfaces, which constrains it more than either theme
alone would.

### 12.2 Accessibility

Large touch targets, WCAG AA contrast at viewing distance, and no
interaction that depends on hover, since the primary device has no
pointer. `CLAUDE.md` protects accessibility from being trimmed, and this
is what that means in practice.

## 13. Observability

The application logs to stdout. systemd captures it into journald, which
already handles rotation and size caps, configured to volatile storage so
logs live in RAM rather than filling the SD card. No log files of our
own.

`GET /api/health` returns version, uptime, per-origin last sync and last
error, database size, and RSS. One URL that answers "what is wrong", read
by the settings screen and by a person over SSH.

## 14. Memory budget

The ceilings are in [ADR-6](adr/0006-1gb-pi4-hardware-floor.md). This
section is about making them bite.

GitHub runners are x86 and there is no Pi in CI, so the real number
cannot gate a merge. Rather than pretend otherwise, the enforcement is
split and each half is labelled.

**Automated, and able to fail.** A frontend bundle-size budget. A backend
import-RSS check on the runner, compared against a committed baseline.
That number is not the Pi's, but it catches somebody adding a large
dependency, which is the regression that actually happens.

**Manual, and a discipline.** `scripts/measure.sh` prints steady-state
RSS per component on real hardware. It is run before any pull request
that touches runtime dependencies, and the numbers go in the pull
request.

A self-hosted runner on the Pi would enforce the real number and is
rejected: it couples the appliance to the pipeline, and a self-hosted
runner reachable from a public repository's fork pull requests is a
genuine exposure.

## 15. Testing

The bugs live in recurrence expansion, conflict resolution, and the sync
state machine, so those get real unit tests: DST transitions, `EXDATE`,
`RECURRENCE-ID` overrides, expired sync tokens, `412` on conditional PUT,
queue replay after an outage.

Google is tested against recorded JSON fixtures through an `httpx` mock
transport. No network, deterministic.

CalDAV is tested against a real Radicale in a CI service container.
Mocking a CalDAV server tests the mock, and CalDAV's real-world quirks
are the whole reason it is hard.

The frontend gets `vitest` on stores and date logic, plus one Playwright
smoke test: load the app, add an event, see it appear. That catches the
wiring failures unit tests never do.

## 16. Schema migrations

`PRAGMA user_version` as the applied marker. Numbered SQL files in
`db/migrations/`, applied in order at startup, each inside a transaction,
with a backup taken before any migration runs. About thirty lines of
standard-library `sqlite3`. Alembic would bring SQLAlchemy, which
[ADR-5](adr/0005-python-fastapi-and-svelte.md) ruled out.

`db/schema.sql` is the declared target. CI asserts that applying every
migration from empty produces it. That catches the drift bug where
somebody edits the schema and forgets the migration, and it is a check
that can actually fail.

Per `CLAUDE.md`, a schema change still gets raised before it is made.
This is the mechanism for applying the answer, not permission to skip the
question.

## 17. Open questions

**Google device authorization grant.** The device flow would be much
better onboarding than the loopback flow: enter a code on your phone
instead of typing a Google password on a touchscreen. Google restricts it
to an allowed scope list, and whether Calendar scopes are on that list
could not be checked, because `developers.google.com` is blocked from
remote sessions.

Verification: read the allowed-scopes list on
`developers.google.com/identity/protocols/oauth2/limited-input-device`
from an unblocked network. If Calendar is eligible, the device flow
becomes the preferred onboarding path and the loopback flow stays as the
fallback. Until then §5.4 stands as written, because it works for any
scope.

**Idle blanking default.** Ships off. Revisit after watching a real
kitchen for a few weeks.

**Landscape.** Supported but second-class. Whether that is good enough
will not be known until it runs on a real panel.
