---
title: Tests and Evaluation (v2)
audience: Engineers and contributors
status: Draft (targeting implementation)
last_updated: 2025-12-25
related_docs:
  - ../README.md
  - ../architecture/braid-data-model.md
  - ../memory/consolidation.md
---

## Purpose

Define the v0 test harness for Elyra v2, focusing on MVP-safe tests first and expanding to tool-grounded tests as capabilities mature.

## MVP-safe tests (v0)

These tests should be implementable without relying on external services:

- **Consistency test**: detect contradictions against high-confidence semantic beads.
- **Re-derivation test**: rerun an independent microagent pass to reproduce a hypothesis.
- **Outcome test**: track success/failure feedback to adjust confidence and ranking.

## Tool-grounded tests (best effort)

When safe tooling exists, add grounding:

- docs/file grounding (project docs, local files)
- web grounding (search + browse)
- code grounding (execute unit tests / snippets)
- perception grounding (re-check sensor inputs)

## Evaluation outputs (for UI and audit)

- hypothesis lifecycle events (proposed/tested/promoted/rejected/decayed)
- confidence and decay changes over time
- tool success rate and latency distributions


