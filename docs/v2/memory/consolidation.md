---
title: Consolidation (Semantic/Procedural) and Dream Drafts (v2)
audience: Engineers and contributors
status: Draft (targeting implementation)
last_updated: 2025-12-25
related_docs:
  - ../README.md
  - ./episodic.md
  - ./semantic.md
  - ./procedural.md
  - ../architecture/runtime-and-scheduling.md
---

## Purpose

Consolidation is the process that derives semantic and procedural memory from the episodic log and keeps summaries current. Consolidators are background workers and are part of the “alive” behavior of Elyra v2.

## Consolidator types

### Semantic consolidator

- reads recent knots/deltas
- extracts concepts/facts/hypotheses
- links semantic beads back to episodic evidence
- updates confidence and contradictions

### Procedural consolidator

- detects repeated successful patterns of action
- proposes new or updated tool/skill/microagent bead versions
- schedules MVP-safe tests (consistency, re-derivation, outcome)

## Dreams and dream drafts

Dreams run after extended idle and generate **draft** deltas/beads that decay unless reinforced.

Guidelines:

- dream outputs are distinguishable by provenance and start with low confidence
- dream-derived semantic items are treated as hypotheses by default
- dream-derived procedural candidates may be created, but require tests before promotion
- decay policies keep dreams available for audit and rare recall, but reduce default retrieval probability over time


