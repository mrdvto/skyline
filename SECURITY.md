# Security policy

Skyline is a personal project with one maintainer. What follows is what
actually happens, not a service level agreement copied from a company that
has a security team.

## Supported versions

There are no releases yet. `main` is the only code there is, and it is the
only thing that gets fixed. When releases start, this section will say
which ones still get patches.

## Reporting a vulnerability

Please do not open a public issue for a security problem.

1. **GitHub private vulnerability reporting** — the Security tab on this
   repository, "Report a vulnerability". This is the preferred channel: it
   is private, it threads, and it needs no email address published
   anywhere.
2. **Email** — <skyline@hellodavid.ca>, if the first channel is not
   working for you.

Useful things to include: what you did, what happened, and why you think it
is exploitable. A proof of concept helps and is not required.

## What to expect

One person reads these, in their own time. A report gets a reply when the
maintainer sees it, which may be a day or may be a couple of weeks. There
is no paid triage rotation behind this and no bounty.

Fixes land on `main`. Once something is deployed anywhere but the
maintainer's kitchen, that will need a real disclosure timeline, and this
file will say so.

## What is worth reporting

Skyline runs on a Raspberry Pi on a home network and, once the sync work
lands, holds a family's calendar and OAuth refresh tokens. The things that
matter most:

- Anything that reads or exfiltrates stored credentials or tokens
- Anything that lets an unauthenticated device on the LAN read or change
  family data
- Anything that turns the kiosk browser into a way onto the host
- Dependency vulnerabilities that are actually reachable from Skyline's
  code paths

The project is pre-release and unfinished, so "this feature does not exist
yet" and "this has no authentication yet" are known, not findings.
