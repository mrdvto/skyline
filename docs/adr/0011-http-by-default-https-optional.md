# 11. HTTP by default, HTTPS as a documented option

- **Status:** Accepted
- **Date:** 2026-09-21

## Context

Skyline is served from a Pi on a home LAN and reached at a `.local`
hostname. TLS on a private network has no easy answer.

A self-signed certificate, or a local CA, has to be installed and trusted
on every device, and again when it expires. On a phone that is several
steps in a settings app. For a non-technical family it is hostile.

A certificate from Let's Encrypt using the DNS-01 challenge does work: a
domain you own, an A record pointing at the private address, no inbound
connection needed, and every device trusts it with no setup. It costs a
domain, a DNS provider API token stored on the Pi, and 90-day renewals.
Many routers block public DNS names that resolve to private addresses as
rebinding protection, so it usually also needs a local DNS override.

A NAS reverse proxy gets to the same place with less work for anyone who
already has a NAS, since most handle certificates themselves. It makes
the NAS load-bearing for the wall calendar.

Tailscale issues trusted certificates too, but joining every device to a
tailnet is remote access, which v1.0 rules out.

Requiring TLS would make a domain a prerequisite for running a family
calendar, which is the wrong bar for the intended audience.

## Decision

v1.0 is designed for and ships on **plain HTTP**. No setup, works for
anybody.

HTTPS is documented as an **optional hardening step**, covering the
Let's Encrypt DNS-01 path and the NAS reverse proxy path, with
self-signed certificates recorded as a poor third and why.

Nothing in the architecture prevents it. The application is served behind
a proxy either way.

The documentation names what HTTPS unlocks, so the tradeoff is visible
rather than discovered: a service worker, PWA installation, and Web
Push, all of which browsers gate behind a secure context. It also makes
the write PIN from [ADR-10](0010-lan-trust-boundary-and-write-pin.md)
confidential in transit.

## Consequences

- Skyline installs with no certificate work. That is the default
  experience.
- Push notifications are out of v1.0. Reminders are shown on the kiosk
  instead. That is a real feature cost, taken deliberately.
- The write PIN is sniffable by someone already on the Wi-Fi until a
  household enables HTTPS.
- No offline capability on phones, since a service worker needs a secure
  context. Offline in v1.0 means the WAN is down, not that the phone has
  left the house.
- If push notifications ever become a requirement, this decision is what
  has to change first, and it needs a superseding ADR.
