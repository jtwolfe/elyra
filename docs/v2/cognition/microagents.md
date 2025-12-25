---
title: Microagents (v2)
audience: Engineers and contributors
status: Draft (targeting implementation)
last_updated: 2025-12-25
related_docs:
  - ../README.md
  - ../architecture/runtime-and-scheduling.md
  - ../architecture/braid-data-model.md
---

## Purpose

Microagents are ephemeral workers spawned during a knot’s think-pass to perform bounded work: calling tools, running tests, proposing hypotheses, or producing summaries. They are not long-lived “agents”; the braid/memory carries continuity.

## Key properties

- spawned on-demand and short-lived
- emit deltas (and optionally create/update bead versions)
- designed to be parallelizable under a shared budget
- may use an LLM, heuristics, or both

## Typical microagent roles

- topic/intent classifier (fork pending confirmation)
- hypothesis re-derivation tester
- consistency checker against high-confidence semantic
- LLM reviewer for “off-topic / not relevant” feedback
- summary improver for complex episodes


