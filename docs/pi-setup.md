# Setting up the Pi

From a blank SD card to a rotated portrait screen showing a web page, with
nothing else running. This covers the appliance only. Installing the Skyline
backend is a separate step and does not exist yet.

The choices here, and the alternatives that lost, are in
[ADR-12](adr/0012-raspberry-pi-os-lite-and-cage.md).

Everything after flashing is done over SSH from another machine. You do not
need a keyboard attached to the Pi.

## A note on what is verified

The commands below have not been run on hardware yet. They are the plan, not
a transcript. Package names and the exact rotation syntax are the two places
most likely to differ from what is written here, and both are flagged where
they appear.

When you run this for real, correct this file as you go. A runbook that
records what was expected is worse than no runbook, because the next person
trusts it.

## 1. Flash the card

Use Raspberry Pi Imager. Choose **Raspberry Pi OS Lite (64-bit)**.

Lite means no desktop. There is no Chromium, no file manager, no login
screen. That is the point: every piece of the display stack gets installed
deliberately.

In Imager's settings, before writing:

- set a hostname, `skyline` is the obvious one
- set a username and **add your SSH public key**, rather than a password
- **enable SSH**
- set locale, timezone and keyboard
- add Wi-Fi credentials if the Pi is not on ethernet

Then boot the Pi and connect:

```
ssh <user>@skyline.local
```

## 2. Record what you actually got

```
cat /etc/os-release
uname -m
free -m
```

The first tells you the Debian base. The second should say `aarch64`. The
third is the baseline memory reading with nothing installed, and it is worth
keeping, because every later measurement is relative to it.

Put the `os-release` version line into ADR-12 in place of this instruction.

## 3. Update, then turn off SD card swap

```
sudo apt update && sudo apt full-upgrade -y
sudo systemctl disable --now dphys-swapfile
sudo apt install -y zram-tools
```

Swapping to an SD card ruins both performance and the card, which is why
[ADR-6](adr/0006-1gb-pi4-hardware-floor.md) rules it out. `zram` compresses
pages in RAM instead. It costs some CPU and buys usable memory back.

Configuration is in `/etc/default/zramswap`. The default size is a
percentage of RAM. Check what it is set to and confirm it is active:

```
zramctl
swapon --show
```

`swapon --show` should list a `/dev/zram0` device and nothing on the SD
card. If a file under `/var` still shows up, `dphys-swapfile` did not
actually stop.

## 4. Rotate the display

The monitor hangs in portrait, so the whole screen rotates, before any
compositor starts.

Find the connector name first:

```
ls /sys/class/drm/
```

You want the one that is connected, usually `card1-HDMI-A-1` or similar,
giving a connector name of `HDMI-A-1`.

Then edit `/boot/firmware/cmdline.txt`. It is **one single line**. Do not
add a newline; append to the end of the existing line, separated by a space:

```
video=HDMI-A-1:1080x1920@60,rotate=90
```

Substitute your connector name and your monitor's native resolution given
as width by height in landscape terms.

This is the flagged step. The `rotate=` parameter and the resolution syntax
should be checked against the current Raspberry Pi documentation rather than
trusted from here, and `rotate=270` may be the one you want depending on
which way the monitor is mounted. Reboot and look at the screen.

```
sudo reboot
```

If the display comes up blank or unrotated, edit the line back out and
reboot. A wrong `video=` parameter does not brick anything.

## 5. Install the kiosk

```
sudo apt install -y cage chromium
```

Package name check: Raspberry Pi OS has historically called the browser
`chromium-browser` while Debian calls it `chromium`. If the install fails,
find the real name:

```
apt-cache search --names-only '^chromium'
```

Test it by hand before making it a service. Run from the Pi's own console,
not over SSH, or use `sudo systemd-run --pty` so it has a TTY:

```
cage -s -- chromium --ozone-platform=wayland --kiosk https://example.com
```

`-s` allows VT switching, so Ctrl+Alt+F2 gets you to a console. ADR-12
records why that hole is deliberately left open for now.

If Chromium refuses to start under Wayland, it may need
`--enable-features=UseOzonePlatform` alongside `--ozone-platform=wayland`,
or it may be falling back to X11 through XWayland. Check with
`echo $WAYLAND_DISPLAY` inside the session.

## 6. Make it start at boot

Create `/etc/systemd/system/skyline-kiosk.service`:

```
[Unit]
Description=Skyline kiosk
After=systemd-user-sessions.service

[Service]
User=<user>
PAMName=login
TTYPath=/dev/tty1
Restart=always
ExecStart=/usr/bin/cage -s -- /usr/bin/chromium --ozone-platform=wayland --kiosk http://localhost:8000

[Install]
WantedBy=graphical.target
```

Then:

```
sudo systemctl enable --now skyline-kiosk
journalctl -u skyline-kiosk -f
```

The URL is a placeholder until the backend exists. Point it at anything to
prove the boot path works.

`Restart=always` means a browser crash puts the calendar back on the wall
without anyone intervening. That matters more than it sounds: the failure
mode of a wall display is that nobody notices for a day.

## 7. Stop the screen blanking

A family calendar that goes dark after ten minutes is not a family
calendar.

Console blanking is disabled with `consoleblank=0` in the same
`cmdline.txt` line as the rotation. Blanking from inside the Wayland
session is a separate question, and wlroots compositors normally leave the
display alone unless an idle daemon is running, so there may be nothing to
do here at all.

Verify rather than assume: leave it for half an hour and see.

## If cage fights you

Swapping to `labwc` is a package, a different `ExecStart`, and a small
config file telling it to open fullscreen with no decorations. Rotation,
the systemd unit's shape, and the web app are all unaffected, because
rotation lives in the kernel command line and Skyline is a web page.

That fallback is the reason rotation went where it did. Use it rather than
fighting a compositor for an evening.

## What comes next

- measured memory: `free -m` with the kiosk running, against the 180MB OS
  and 500MB browser ceilings in [ADR-6](adr/0006-1gb-pi4-hardware-floor.md)
- a bootstrap script that does all of the above, once the manual version is
  known to work
- the backend, at which point the placeholder URL becomes real
