# 13. Google Calendar authorization by loopback, with httpx and no credentials library

- **Status:** Proposed
- **Date:** 2026-09-22

## Context

[ADR-5](0005-python-fastapi-and-svelte.md) committed to `google-auth` plus
`httpx` against Google's REST endpoints rather than `google-api-python-client`.
It recorded the choice without a reason. The reason is written in three other
places -- `CLAUDE.md`, `CONTRIBUTING.md` and `../sdd.md` §5.2 all say
`google-api-python-client` loads large discovery documents into memory -- and
it was a reputation rather than a measurement. The spike in
`../../spikes/google-calendar/` measured it.

```
stack                            RSS  over baseline
baseline                      8.7 MB              -
httpx only                   22.0 MB       +13.3 MB
google-auth + httpx          40.4 MB       +31.7 MB
google-api-python-client     40.4 MB       +31.7 MB
```

x86, Python 3.11.15. The ratios carry to arm64; the absolute numbers do not.

The two libraries cost the same. Building the Calendar service from its
bundled discovery document accounts for 0.61MB of `google-api-python-client`'s
footprint, so discovery documents are not where its memory goes and the reason
those three files give is wrong. That figure is for the static discovery path;
the dynamic one needs an API key and was not measured, which the spike README
says in as many words.

What the table does show is that `google-auth` is expensive, and for work this
application never does. Marginally it is nearly the whole stack: 18.5MB added
on top of `httpx`, against 1.0MB for `httpx` added on top of it. Importing `google.oauth2.credentials` costs 23MB,
because it reaches `google.auth.jwt` and therefore `cryptography` and the
OpenSSL bindings. `google.auth.transport.requests` then pulls in `requests`
beside the `httpx` already loaded, so the process carries two HTTP clients.

Refreshing a user OAuth token is a form POST to a documented URL that returns
JSON. No signature is verified locally. The spike does it in ten lines.

Separately, #29 asked whether Google's device-code flow permits Calendar
scopes, because the answer decides whether a family member authorizes from
their phone or types a Google password on a wall-mounted touchscreen. It is
still unanswered; see below.

## Decision

Proposed, not accepted. CLAUDE.md lists the Google OAuth and credential
storage design as ask-before-proceeding, and one of the questions underneath
this is still open.

**Drop `google-auth`.** Do the OAuth token exchange and refresh with `httpx`
directly, against `https://oauth2.googleapis.com/token`. This saves 18.5MB of
a 200MB backend budget and removes a dependency whose sole remaining job would
be a POST.

**Keep the rest of ADR-5.** `httpx` against the REST endpoints stands. The
discovery-document reasoning was wrong, but the conclusion survives on other
grounds: `google-api-python-client` costs the same memory,
adds a second HTTP stack, and gives back a dynamically generated client that
is harder to reason about than a URL.

**Authorize by loopback redirect with PKCE**, binding `127.0.0.1` on an
ephemeral port. Google documents this for installed applications and it is
known to work.

**Store the refresh token outside the repository**, in a file owned by the
service user with mode 0600. This is the part most in need of a second
opinion, and no code has been written for it.

## The open question, stated as open

Whether Google permits its device-code flow for Calendar scopes is not known.

It could not be resolved from a remote session. The scope allow-list is
published on `developers.google.com`, which is blocked at the proxy tunnel,
and no reachable source quoted it. The device endpoint at
`https://oauth2.googleapis.com/device/code` is reachable, but it validates
`client_id` before it looks at `scope`, so it returns `invalid_client` for a
Calendar scope, for `email profile`, and for a Drive scope alike. It will not
answer without a real OAuth client, and none exists yet.

With a client, one curl settles it: a `device_code` in the response means
Calendar is allowed and this ADR should be rewritten around device code;
`invalid_scope` means loopback is the answer and this ADR is right for the
reason it says.

Loopback works either way, which is why it is proposed rather than blocked on.
What changes is the experience. Under loopback the person authorizing has to
be at a browser that can reach the Pi's loopback port, which in practice means
an SSH tunnel or doing it on a laptop and copying the refresh token over.
Under device code they open a short URL on their phone. For an appliance a
family sets up once, that difference is most of the setup.

A second question, from `../google-calendar-setup.md` and equally unverified:
an External OAuth app left in Google's "Testing" status appears to issue
refresh tokens that expire after roughly a week. If that holds, the appliance
needs re-authorizing every seven days and no arrangement of flows fixes it.
That is a larger problem than which flow to use, and it should be answered
first.

## Consequences

- One fewer runtime dependency, and 18.5MB back. Measured on x86, to be retaken
  on the Pi before it is quoted against ADR-6's ceiling.
- The token refresh becomes Skyline's code to maintain. It is a POST with four
  form fields; the risk is small and the failure is loud.
- No `cryptography` in the backend on account of Google. Something else may
  still pull it in, and if it does, this decision's saving shrinks to the
  `requests` half.
- `google-api-python-client` stays out, but the discovery-document reason for
  it is retired. `CLAUDE.md` and `CONTRIBUTING.md` are corrected in the same
  change; `docs/sdd.md` §5.2 carries it too and is corrected there as well,
  though the `google-auth` half of that section waits on this ADR being
  accepted.
- Setup requires a browser that can reach the Pi's loopback interface. The
  device-code flow would remove that, and may yet.
- The spike code is throwaway. The real sync worker is a background task per
  SDD 3.1, not a script, and nothing in `spikes/` should be imported.
