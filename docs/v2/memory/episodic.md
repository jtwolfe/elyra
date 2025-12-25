---
title: Episodic Memory (v2)
audience: Engineers and contributors
status: Draft (targeting implementation)
last_updated: 2025-12-25
related_docs:
  - ../README.md
  - ../architecture/braid-data-model.md
  - ../architecture/context-ribbon.md
---

## Purpose

Episodic memory is the **source-of-truth log** for Elyra v2: a time-ordered (potentially branching) chain of deltas and immutable knots. Everything else (semantic/procedural) is derived from episodic evidence.

## What lives in episodic memory

- user messages and assistant outputs
- tool calls/results
- microagent runs
- knot summaries and thought-summary bead references
- episode membership/edges (as overlays referencing knots)
- dream events (explicit provenance, low confidence by default)

## Knots vs episodes

- **Knot**: immutable checkpoint over a delta range; the unit of “computed state.”
- **Episode**: overlapping overlay grouping knots/deltas by topic/intent/time.

Every knot has a primary episode (at minimum “session @ timecode”), but a knot may belong to multiple episodes.

## Replay and narrative continuity

Episodic memory enables:

- **Replay**: re-simulating a sequence of knots/deltas to understand why a decision was made.
- **Time-based recall**: retrieving what happened around a time window.
- **Continuity across forks**: carrying the last 15–30 messages (or last 5–10 minutes of knots) plus anchor quotes into new forks.


