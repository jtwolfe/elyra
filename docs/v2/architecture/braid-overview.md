---
title: Braid Architecture Overview
audience: Engineers and contributors
status: Draft (targeting implementation)
last_updated: 2025-12-25
related_docs:
  - ../README.md
  - ./braid-data-model.md
  - ../memory/episodic.md
---

## Overview

Elyra v2 models the system as a **Braid**: an append-only stream of deltas with periodic immutable checkpoints (“knots”), plus overlapping “episodes” that organize knots into narrative/topic/intent groupings. Elyra composes two core subsystems:

- **LargeMemoryModel (LMM)**: episodic/semantic/procedural memory, beads, consolidation, retrieval/ribbon building
- **LargeCognitiveModel (LCM)**: knot processing (think/speak), microagents, tests, fork detection

Elyra itself is the **composition layer**: API/UI + configuration and wiring of LMM and LCM.

## High-level flow

```mermaid
flowchart TD
  inputs[Inputs] --> deltas[AppendDeltas]
  deltas --> knotThink[ThinkPass]
  knotThink --> knotCommit[KnotCommit]
  knotCommit --> ribbon[BuildContextRibbon]
  ribbon --> knotSpeak[SpeakPass]
  knotSpeak --> response[UserResponse]
  deltas --> episodic[EpisodicLog]
  episodic --> consolidators[Consolidators]
  consolidators --> semantic[SemanticDerived]
  consolidators --> procedural[ProceduralDerived]
```

## Key design choices

- **Aliveness over perfection**: continuous background metacognition and thought; dreams produce low-confidence hypotheses.
- **No tool calls in speak**: tool use happens during think-pass.
- **Forks are conservative**: forks are pending-first, confirmed by classifier, and adaptively tuned.
- **Reasoning as beads**: narrative thought summaries are stored, inspectable, and optionally used as context inputs; raw CoT is never included by default.


