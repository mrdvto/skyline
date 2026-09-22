#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Authorize against Google and read events, using httpx and nothing else.

Throwaway. This exists to prove the approach and to be thrown away, not to
be the sync worker. It is deliberately one file with no abstraction in it.

What it demonstrates, and why each part is here:

  * The loopback redirect flow with PKCE, which is what Google supports for
    installed applications. Whether the device-code flow is permitted for
    Calendar scopes is unresolved -- see README.md -- so this implements
    the fallback that is known to work.
  * A token refresh that is one POST, with no `google-auth` behind it.
    `google.oauth2.credentials` pulls in `cryptography` for JWT
    verification that a refresh-token flow never performs. measure.py has
    the number.
  * A single read of the events list, paginated, with the timezone handling
    left to the caller because that is the real application's problem.

Credentials come from the environment. Nothing is written to the
repository, per CLAUDE.md, and the refresh token is printed for the
operator to put somewhere outside it:

    export SKYLINE_CLIENT_ID=... SKYLINE_CLIENT_SECRET=...
    python3 client.py          # authorize, print a refresh token
    SKYLINE_REFRESH_TOKEN=... python3 client.py   # read events
"""

import base64
import hashlib
import http.server
import os
import secrets
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone

import httpx

AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
EVENTS = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

# Read-only. The spike does not write, and a scope it does not need is a
# scope the consent screen asks a family member to grant for no reason.
SCOPE = "https://www.googleapis.com/auth/calendar.readonly"


class _Handler(http.server.BaseHTTPRequestHandler):
    """Catches the one redirect Google sends back to the loopback port."""

    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        # The state check is not optional even in a spike: without it this
        # endpoint accepts an authorization code from anything else on the
        # machine that can reach the loopback port.
        got = query.get("state", [""])[0]
        if secrets.compare_digest(got, self.server.expected_state):
            self.server.code = query.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Done. Close this tab.")

    def log_message(self, *args):
        pass


def wait_for_code(server, state):
    """Serve exactly one request and return the code it carried, if valid.

    Split out of authorize() so the state check can be driven over a real
    socket by test_client.py. Everything else in the flow needs Google at
    the other end; this part does not.
    """
    server.expected_state = state
    server.code = None
    # Without this, a consent screen someone closed leaves the spike
    # blocked on accept() with no way out but ctrl-c.
    server.timeout = 300
    server.handle_request()
    return server.code


def authorize(client_id, client_secret):
    """Run the loopback flow and return a refresh token.

    Google allows any port on 127.0.0.1 for an installed-app client, so
    this binds port 0 and lets the OS choose. That avoids a fixed port
    that might be taken on the Pi.
    """
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )
    state = secrets.token_urlsafe(16)
    server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    redirect = f"http://127.0.0.1:{server.server_port}"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "access_type": "offline",
        # Without this, a second authorization of an already-consented
        # client returns no refresh token and the flow looks broken.
        "prompt": "consent",
    }
    print("Open this, then sign in:\n")
    print(f"  {AUTH}?{urllib.parse.urlencode(params)}\n")
    try:
        code = wait_for_code(server, state)
    finally:
        server.server_close()
    if not code:
        sys.exit("no code came back: timed out, denied, or wrong state")

    r = httpx.post(
        TOKEN,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "code_verifier": verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect,
        },
    )
    r.raise_for_status()
    return r.json()["refresh_token"]


def access_token(client_id, client_secret, refresh_token):
    """One POST. This is the whole of what `google-auth` was carried for."""
    r = httpx.post(
        TOKEN,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    r.raise_for_status()
    return r.json()["access_token"]


def events(token, days=7):
    """Events in the next `days`, following pagination to the end.

    `singleEvents` asks Google to expand recurrence server-side. The real
    sync worker will not do that -- it stores the series and expands
    locally, per SDD 4.4 -- but this spike is reading, not syncing.
    """
    now = datetime.now(timezone.utc)
    params = {
        "timeMin": now.isoformat(),
        "timeMax": (now + timedelta(days=days)).isoformat(),
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": 250,
    }
    with httpx.Client(headers={"Authorization": f"Bearer {token}"}) as client:
        while True:
            r = client.get(EVENTS, params=params)
            r.raise_for_status()
            body = r.json()
            yield from body.get("items", [])
            page = body.get("nextPageToken")
            if not page:
                return
            params["pageToken"] = page


def main():
    client_id = os.environ.get("SKYLINE_CLIENT_ID")
    client_secret = os.environ.get("SKYLINE_CLIENT_SECRET")
    if not (client_id and client_secret):
        sys.exit("set SKYLINE_CLIENT_ID and SKYLINE_CLIENT_SECRET")

    refresh_token = os.environ.get("SKYLINE_REFRESH_TOKEN")
    if not refresh_token:
        refresh_token = authorize(client_id, client_secret)
        print(f"\nSKYLINE_REFRESH_TOKEN={refresh_token}\n")
        print("Keep that out of the repository. Re-run with it set.")
        return

    token = access_token(client_id, client_secret, refresh_token)
    for event in events(token):
        start = event["start"].get("dateTime") or event["start"].get("date")
        print(f"{start}  {event.get('summary', '(no title)')}")


if __name__ == "__main__":
    main()
