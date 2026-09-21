# 12. Raspberry Pi OS Lite 64-bit, with cage as the kiosk compositor

- **Status:** Accepted
- **Date:** 2026-09-21

## Context

[ADR-6](0006-1gb-pi4-hardware-floor.md) committed to "Raspberry Pi OS Lite
with a minimal kiosk compositor" and left it there. That was enough while
there was no hardware. Now there is a Pi on the desk, and three questions
have to be answered before the first package is installed: which
architecture, which compositor, and where screen rotation happens.

These are cheap to change in the sense that reflashing a card takes ten
minutes. They are expensive in the sense that the kiosk boot path is the
one part of Skyline a non-technical family cannot recover from, so it
needs to be written down rather than assembled from whatever a tutorial
suggested.

### Architecture

A 32-bit armhf userland uses less memory than arm64, mostly through
smaller pointers. Roughly 10%, though that is an estimate and not a
measurement on this hardware. Against a 500MB browser ceiling, 10% is
worth naming.

The argument against armhf is that it is a shrinking platform. Upstream
attention, Chromium builds, and Debian's own long-term plans all point at
arm64. Designing the memory budget around a userland that is being
retired means the budget expires with it.

There is also a diagnostic argument. If Skyline only fits in 1GB on
32-bit, the design is wrong and it is better to find that out now than to
hide it behind an architecture choice.

### Compositor

Something has to own the display. Raspberry Pi OS Lite ships no desktop,
so this is a deliberate install either way.

`cage` is a Wayland compositor that runs one application fullscreen and
nothing else. There is no window management to configure off, because
there is no window management.

`labwc` is the window manager Raspberry Pi OS itself uses. It is the
best-documented path on this hardware, which matters when a maintainer is
debugging alone. It is also a general-purpose window manager that would
be configured to stop behaving like one.

X11 with openbox or matchbox is the recipe most Pi kiosk tutorials use. It
needs an X server and a separate window manager, which is two more
processes than a single-application appliance needs, on the machine with
the least memory.

### Rotation

The monitor hangs in portrait. cage has no rotation option: its man page
lists `-d`, `-D`, `-h`, `-m`, `-s` and `-v`, and none of them rotate an
output. So rotation cannot live in the compositor even if we wanted it
there.

## Decision

**Raspberry Pi OS Lite, 64-bit.** The current release, whatever Raspberry
Pi Imager offers. The Debian base is recorded in the setup runbook from
`/etc/os-release` on first boot rather than asserted here, because a
codename written from memory is a codename that is wrong later.

**cage plus Chromium**, started by a systemd unit on a TTY.

**Rotation is configured in KMS**, through the `video=` kernel parameter
in `/boot/firmware/cmdline.txt`. It happens below the compositor, so it
survives replacing cage, and it survives replacing Chromium with `cog` as
[ADR-4](0004-web-app-in-kiosk-browser.md) allows.

The steps are in [docs/pi-setup.md](../pi-setup.md).

## Consequences

- The appliance runs one application with no way out of it by design,
  rather than by configuration that could be missed.
- Less documentation to lean on than labwc or X11 would offer. The setup
  runbook carries more weight because of it, and needs to record what
  actually worked on the device, not what was expected to.
- Swapping to labwc stays cheap: a package, a different systemd unit, and
  the rotation and the web app are untouched. The runbook says so
  explicitly so the fallback is a documented step rather than a redesign.
- VT switching is enabled (`cage -s`) so there is a way to a console when
  something goes wrong. That is a deliberate hole in the kiosk lock, taken
  because an unrecoverable wall display is worse than a recoverable one.
  Closing it is a later decision, once the thing is stable.
- If the memory budget fails on arm64, 32-bit is the experiment to run
  before the design is blamed. That is a reflash, not a rewrite.
- Raspberry Pi OS Lite is a Debian derivative, so `cage`, `chromium` and
  `zram-tools` come from the distribution. No third-party apt repositories,
  nothing built from source on the Pi.
