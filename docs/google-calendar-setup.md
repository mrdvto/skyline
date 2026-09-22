# Getting a Google OAuth client for Skyline

What you need before Skyline can read a Google calendar: a Cloud project, an
OAuth consent screen, and a client ID. It is free, it takes about fifteen
minutes, and most of that is waiting for pages to load.

## A note on what is verified

Nobody has run this yet. It was written alongside the spike in
`../spikes/google-calendar/`, in a session that could not reach
`console.cloud.google.com` or `developers.google.com` -- both are blocked at
the proxy tunnel, so none of the screen names below were read off the console
while writing them.

Google renames things in that console often. Treat the names as approximate
and the sequence as the real content. When you run it, correct this file in
place, the way `pi-setup.md` asks to be corrected. A runbook nobody has
followed is a guess with formatting.

## The steps

1. Sign in to `console.cloud.google.com` with the account that owns the
   calendar. For a family calendar shared to several accounts, use the owner's
   -- a shared calendar can be read through any account it is shared with, but
   the one that owns it will not lose access when somebody leaves.

2. Create a project. Name it something you will recognise in two years.

3. Enable the Google Calendar API for that project. Nothing works before this,
   and the error when it is missing names the API and a URL to enable it, so
   if you skip it you will find out quickly.

4. Configure the OAuth consent screen. Choose "External" unless you have a
   Workspace domain, which for a household you do not.

   Add yourself as a test user. An External app that has not gone through
   Google's verification only works for accounts listed there, which is fine:
   verification exists for applications with users who are strangers.

   Add the scope `https://www.googleapis.com/auth/calendar.readonly` and
   nothing else. Skyline does not write to Google yet, and a scope you do not
   need is one the consent screen asks a family member to grant for no reason.

5. Create credentials, type "OAuth client ID", application type **Desktop
   app**. Not "Web application". The desktop type is what permits the loopback
   redirect to `127.0.0.1` on any port, which is the flow
   `spikes/google-calendar/client.py` implements.

6. Copy the client ID and client secret. They go in the environment, never in
   this repository:

   ```
   export SKYLINE_CLIENT_ID=...apps.googleusercontent.com
   export SKYLINE_CLIENT_SECRET=...
   ```

   The "secret" in a desktop OAuth client is not really a secret -- it ships
   inside any installed application that uses one, and Google's own
   documentation says as much. It still does not go in the repository. A rule
   with exceptions is a rule nobody can check.

## The seven-day problem

**Everything in this section is recalled, not checked.** Google's
documentation could not be reached from the session that wrote it, and a
wrong answer here is expensive enough that it should be confirmed against the
console before anyone plans around it.

The recollection: an External app left in "Testing" status issues refresh
tokens that expire after about a week. If that is right, an appliance on a
wall needs re-authorizing every seven days, which no family will do, and it is
the one thing that could make this approach unworkable on a consumer account.

The ways out, assuming the problem is real:

- Publish the app to "In production". Whether that is a button or a
  verification process depends on whether Google classes
  `calendar.readonly` as a sensitive scope. Also unchecked.
- Use a Workspace account, where an Internal app is not limited this way.
  Costs money, and most households do not have one.

First person with console access should answer both and correct this section.
[ADR-13](adr/0013-google-calendar-authorization-flow.md) records it as open
and blocking.

## Checking it worked

```
cd spikes/google-calendar
python3 -m venv .venv && .venv/bin/pip install httpx
.venv/bin/python client.py
```

It prints a URL. Open it on any machine, sign in, grant access. The browser
lands on a page saying "Done. Close this tab." and the terminal prints a
refresh token. Set `SKYLINE_REFRESH_TOKEN` to it and run the same command
again; you get a week of events, one per line.

If the browser cannot reach the Pi's loopback port -- and it cannot, if you
are authorizing from a phone -- run the spike over SSH with port forwarding,
or run it on the machine with the browser and move the refresh token to the
Pi afterwards. That awkwardness is the whole reason the device-code flow is
worth chasing, and why ADR-13 leaves it open.
