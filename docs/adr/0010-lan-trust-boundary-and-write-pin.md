# 10. The LAN is the trust boundary, and writes need a household PIN

- **Status:** Accepted
- **Date:** 2026-09-21

## Context

Skyline shows a family's calendar on a wall screen that anybody in the
kitchen can touch. That screen is unauthenticated by its nature: putting
a login on it would mean a permanently signed-in session anyway.

People in Skyline are profile rows used for ownership and colour, not
accounts. There are no passwords and no sessions.

v1.0 also lets family phones on the LAN read the calendar and quick-add
events, which widens who can write from "anyone in the kitchen" to
"anything on the network". A home LAN carries guest devices, children's
tablets, and a television browser.

Real authentication was rejected: it is heavy for a family home, and the
kiosk would undermine most of its benefit. Restricting writes by source
subnet was also rejected, because a guest device sits on the same subnet
and would pass, so it would look like a control while being none.

## Decision

The LAN is the trust boundary. Skyline is not hardened against a hostile
LAN and assumes the household keeps it off guest networks and off any
network carrying untrusted devices.

Reads are open to anything that can reach the backend.

**Writes require a household PIN**, sent in a header. A device is
enrolled once by entering the PIN on a settings screen, after which it is
held in `localStorage`. The kiosk and each family phone are asked once.
Rotating the PIN means changing it in the configuration file and
re-enrolling devices.

Because a PIN is short enough to type on a phone and read off the fridge,
write endpoints are rate-limited per client address and repeated failures
are logged.

Regardless of any of the above, and never trimmed: input validation at
the API boundary, no credentials in responses, CORS restricted to the
app's own origin, and no path exposing Skyline beyond the LAN.

## Consequences

- A guest's phone, a child's tablet, or a television browser cannot
  change the family calendar by wandering onto it.
- The PIN crosses the network in the clear while HTTPS is optional
  ([ADR-11](0011-http-by-default-https-optional.md)). Someone with the
  Wi-Fi password who wants to capture it can. This stops casual and
  accidental writes, not a determined person already inside the network.
  Enabling HTTPS closes it.
- This is not the "no authentication at all" model originally intended.
  It is one shared secret and no user accounts, which stays far short of
  sessions, password storage, or a reset flow.
- Exposing Skyline beyond the LAN would retire this decision entirely and
  needs its own ADR.
