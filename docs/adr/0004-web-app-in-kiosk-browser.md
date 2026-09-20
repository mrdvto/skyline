# 4. Web application rendered in a kiosk browser

- **Status:** Accepted
- **Date:** 2026-09-20

## Context

Skyline runs on a Raspberry Pi with an attached touch monitor. Family
members will also want access from phones and tablets. The options
considered were a native toolkit (Qt/PySide6), Flutter targeting Linux,
Tauri, and a web application displayed fullscreen in a kiosk browser.

## Decision

Skyline is a **web application**, served by a local backend on the Pi and
displayed fullscreen by a kiosk browser on the attached monitor.

Chromium is the initial renderer.

## Consequences

- Phone and tablet access requires no extra work: the same application,
  any browser on the LAN.
- Development happens on a laptop; only kiosk integration needs real
  hardware.
- This is the proven pattern for Pi dashboards (MagicMirror, DAKboard,
  Home Assistant), so the failure modes are well documented.
- **The browser is the largest single memory consumer** — 350–500MB of a
  1GB budget. This is the main cost of the decision.
- Long-running kiosk browsers leak. A scheduled renderer restart must be
  designed in from the start, not added after the first crash.
- If Chromium proves too heavy, the renderer can be swapped for `cog`
  (a WebKit/WPE kiosk browser built for embedded devices) without touching
  application code. Serving a normal web app keeps this door open.
- Rejected: Qt/PySide6 (would need a separate API and app for phones),
  Flutter (Linux ARM64 is not first-class; cross-compilation required),
  Tauri (steepest learning curve, no better phone story).
