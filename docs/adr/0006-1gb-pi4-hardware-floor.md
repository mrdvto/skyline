# 6. Raspberry Pi 4 with 1GB RAM is the hardware floor

- **Status:** Accepted
- **Date:** 2026-09-20

## Context

Skyline targets "Raspberry Pi 4 and higher". The 1GB Pi 4 is the smallest
member of that family and is the maintainer's own hardware. Whether it is
the supported floor or merely a development machine changes almost every
downstream decision.

## Decision

**The 1GB Pi 4 is the supported floor.** Skyline must run well there, not
merely start.

Working budget of 1024MB:

| Component | Ceiling |
|---|---|
| OS + kiosk compositor | 180MB |
| Browser | 500MB |
| Backend (Python, SQLite, sync workers) | 200MB |
| GPU split | 50MB |
| Headroom | ~90MB |

## Consequences

- **Raspberry Pi OS Lite** with a minimal kiosk compositor. No full
  desktop environment; it would consume most of the OS budget by itself.
- **Lean dependencies are a standing rule**, not a preference. Import cost
  is checked before any library is added.
- **`zram` for swap, never the SD card.** Swapping to SD destroys
  performance and the card. Memory pressure must be handled by using less,
  not by spilling.
- **Steady-state RSS is a tracked metric.** A change that raises it is a
  regression and must be reported with numbers in its PR.
- Browser memory growth over long uptimes has to be managed deliberately
  (ADR-4).
- Development on the target hardware is slower and more constrained than on
  a larger Pi. Accepted: it keeps the constraint honest and continuously
  visible rather than discovered at release time.
- Anything above 1GB gets a comfortable experience for free.
