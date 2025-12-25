---
title: Observability and UI (v2)
audience: Engineers and contributors
status: Draft (targeting implementation)
last_updated: 2025-12-25
related_docs:
  - ../README.md
  - ../architecture/braid-data-model.md
  - ../architecture/runtime-and-scheduling.md
---

## Purpose

Define what Elyra v2 exposes for debugging and user trust: visible internal thoughts, knot summaries, and expandable inspection of deltas and beads.

## UX goals

- Default experience feels “alive”: show internal thought summaries (“I…”) and background activity (metacognition, dreams).
- Do not overwhelm: default view is summaries; details are expandable.
- Full audit trail: users/developers can inspect what was used, what was tested, and what was promoted.

## Trace model (v0)

### Primary UI objects

- **Knot summary**: short description of what happened and why.
- **Thought summary**: narrative “I…” voice plus structured fields (assumptions/hypotheses/tests/confidence).
- **Tool trace**: planned vs executed, with results.
- **Hypothesis trace**: proposed → tested → promoted/rejected/decayed.

### Expandability

From a knot:

- expand to see **deltas** produced during the knot
- each delta can expand to show referenced **beads** and versions
- episodes can expand to show their summaries, anchor quotes, and linked episodes

## Safety/discipline defaults

- Raw/verbatim chain-of-thought is not shown by default and is not included in context.
- Reasoning summaries are visible and are the primary introspection artifact.
- Dream-origin artifacts are distinguishable and confidence-weighted.


