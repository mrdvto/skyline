# Spike: Google Calendar against the REST API

Throwaway code for [issue #29](https://github.com/mrdvto/skyline/issues/29).
It is here to be measured and argued with, then deleted once the real sync
worker exists. Nothing in `skyline/` should import it.

## What it found

The claim in [ADR-5](../../docs/adr/0005-python-fastapi-and-svelte.md) is that
`google-auth` plus `httpx` costs less memory than `google-api-python-client`,
because the latter loads large discovery documents. The first half of that is
true by a rounding error. The second half is the wrong reason.

```
stack                            RSS  over baseline    import
baseline                      8.7 MB              -   0.000 s
httpx only (this spike)      22.0 MB       +13.2 MB   0.055 s
google-auth + httpx          40.4 MB       +31.7 MB   0.146 s
google-api-python-client     40.3 MB       +31.6 MB   0.136 s

python 3.11.15 on linux, x86
```

Reproduce with `python3 measure.py`. Three consecutive runs agreed to within
0.2MB.

Two things fall out of that table.

**The two stacks ADR-5 compared cost the same.** 31.7MB against 31.6MB is not
a difference. Building the Calendar service from its bundled discovery
document costs 0.5MB, measured separately, so the discovery document is not
where `google-api-python-client`'s memory goes.

**`google-auth` is the expensive half of the stack ADR-5 chose.** Importing
`google.oauth2.credentials` alone costs 23MB, because it reaches
`google.auth.jwt`, which imports `cryptography`, which loads the OpenSSL
bindings. Importing `google.auth.transport.requests` adds `requests` on top of
the `httpx` already there, so the process carries two HTTP clients.

A Pi refreshing an OAuth token does not verify a JWT signature. It posts a
refresh token to `https://oauth2.googleapis.com/token` and reads JSON back
over TLS that `httpx` has already validated. `client.py` does exactly that in
ten lines, and the library those ten lines replace costs 18MB of a 200MB
budget.

The honest caveat, from #29 and repeated here so it does not get lost: these
numbers are x86. The ratio between stacks will carry to the Pi's arm64; the
absolute figures will not, and must be retaken on the hardware before anyone
quotes them against the 200MB ceiling. `cryptography` ships a compiled
extension, so its arm64 cost is the one most likely to differ.

## What it did not answer

**Whether Google's device-code flow permits Calendar scopes is still open.**
It could not be checked from this session, and the answer was not guessed.

`developers.google.com` is blocked at the proxy tunnel in remote sessions --
a host CLAUDE.md did not have on its blocked list before this spike, and now
does. The scope allow-list lives on that host and nowhere else that could be
reached. Search results referenced the list without quoting it.

The device endpoint itself was probed directly, which is reachable:

```
$ curl -s -X POST https://oauth2.googleapis.com/device/code \
    -d client_id=000000000000-notarealclient.apps.googleusercontent.com \
    --data-urlencode scope=https://www.googleapis.com/auth/calendar.readonly
{"error": "invalid_client", "error_description": "The OAuth client was not found."}
```

The same error comes back for `email profile`, which is certainly allowed, and
for a Drive scope. Google validates the client before it looks at the scope,
so the endpoint will not answer this question without a real OAuth client.

Once a Cloud project exists, that same curl with a real `client_id` settles it
in one call: a `device_code` in the response means Calendar is allowed, and
`invalid_scope` means it is not. Two minutes, and it blocks the ADR.

So `client.py` implements loopback, which is documented as supported for
installed applications and is the fallback #29 named. The proposal in
[ADR-13](../../docs/adr/0013-google-calendar-authorization-flow.md) is written
around that, with the device-code question marked open inside it.

## Running it

You need a Google Cloud project with an OAuth client of type "Desktop app".
[docs/google-calendar-setup.md](../../docs/google-calendar-setup.md) has the
console steps. None existed when this was written, so the live read below is
the one part of this spike that has not been run.

```
python3 -m venv .venv && .venv/bin/pip install httpx
export SKYLINE_CLIENT_ID=... SKYLINE_CLIENT_SECRET=...

.venv/bin/python client.py     # prints a URL, waits for the redirect,
                               # prints a refresh token

SKYLINE_REFRESH_TOKEN=... .venv/bin/python client.py   # prints a week of events
```

`measure.py` needs more than that, since it imports the libraries it is
comparing:

```
.venv/bin/pip install google-auth google-api-python-client
.venv/bin/python measure.py
```

No credential is read from a file or written to one. The refresh token is
printed for you to put somewhere outside this repository, and CLAUDE.md means
that literally: not in a test, not in an example.

## The checks

`python3 test_client.py` covers the two things in `client.py` that can be
wrong without looking wrong: pagination stopping after the first page, and the
loopback handler accepting a callback whose `state` does not match. Both were
broken on purpose and confirmed to fail before being left in place.

Everything else in the file is protocol. It is wrong or right depending on
what Google does with it, and no local check can tell you which.
