#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Checks for the two pieces of client.py that can be wrong silently.

No live credentials, so this cannot prove the flow works against Google.
It proves the parts that are logic rather than protocol: that pagination
follows nextPageToken to the end, and that the loopback handler ignores a
callback carrying the wrong state.

Both were picked because they fail quietly. A first-page-only read looks
like a calendar with not many events on it, and a missing state check
looks like nothing at all until someone uses it.

    python3 test_client.py
"""

import http.server
import threading
import urllib.request

import client
import httpx

PAGES = [
    {"items": [{"summary": "one"}], "nextPageToken": "p2"},
    {"items": [{"summary": "two"}]},
]


def test_pagination_follows_every_page():
    seen = []

    def handle(request):
        seen.append(dict(request.url.params).get("pageToken"))
        return httpx.Response(200, json=PAGES[len(seen) - 1])

    transport = httpx.MockTransport(handle)
    original = client.httpx.Client
    client.httpx.Client = lambda **kw: original(transport=transport, **kw)
    try:
        got = [event["summary"] for event in client.events("token")]
    finally:
        client.httpx.Client = original

    assert got == ["one", "two"], got
    assert seen == [None, "p2"], seen


def callback(query):
    """Drive wait_for_code over a real socket with the given query string.

    A real loopback request rather than a constructed handler, because the
    thing being checked is what the server does with what arrives on the
    wire.
    """
    server = http.server.HTTPServer(("127.0.0.1", 0), client._Handler)
    result = {}
    thread = threading.Thread(
        target=lambda: result.update(code=client.wait_for_code(server, "right"))
    )
    thread.start()
    urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/?{query}").read()
    thread.join(timeout=5)
    return result["code"]


def test_loopback_takes_the_code_when_state_matches():
    assert callback("code=abc&state=right") == "abc"


def test_loopback_ignores_a_wrong_or_missing_state():
    assert callback("code=abc&state=wrong") is None
    assert callback("code=abc") is None


if __name__ == "__main__":
    for name, check in sorted(globals().items()):
        if name.startswith("test_"):
            check()
            print(f"ok: {name[5:].replace('_', ' ')}")
