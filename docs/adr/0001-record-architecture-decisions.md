# 1. Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-09-20

## Context

Skyline is a long-lived project, built mostly by an AI agent across many
sessions that do not share memory. Decisions made in conversation evaporate
when the session ends. Without a durable record, later sessions re-litigate
settled questions, or silently contradict them.

## Decision

Significant architectural decisions are recorded as ADRs in `docs/adr/`,
numbered sequentially, following Michael Nygard's format.

An ADR is warranted when a decision is expensive to reverse, constrains
future work, or would otherwise be re-argued later. Routine implementation
choices do not need one.

ADRs are immutable once accepted. A decision that changes gets a **new**
ADR that supersedes the old one; the original stays, marked `Superseded
by ADR-NNNN`.

## Consequences

- Any session can recover the reasoning behind the current design.
- Contradicting a recorded decision requires stating why, in writing.
- Small ongoing cost: each significant decision needs a short document.
