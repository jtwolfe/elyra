---
title: Semantic Memory (v2)
audience: Engineers and contributors
status: Draft (targeting implementation)
last_updated: 2025-12-25
related_docs:
  - ../README.md
  - ./episodic.md
  - ../architecture/braid-data-model.md
---

## Purpose

Semantic memory is **derived knowledge** extracted from episodic evidence: concepts, facts, associations, contradictions, and “what means what” in a project/user context.

Semantic memory is confidence-weighted and provenance-aware. It is not assumed to be ground truth.

## What semantic memory stores (examples)

- concepts/entities and their associations
- facts and hypotheses with confidence
- contradiction edges (“A conflicts with B”)
- usage semantics (“procedure/tool X applies to intent/topic Y”)
- topic graph indexing episodes and knots

## Provenance and confidence

- Provenance (`user`, `tool`, `dream`, etc.) is tracked separately from confidence.
- Dream-derived semantic items typically start with low confidence and decay unless reinforced.

## How semantic is produced

Semantic consolidators read episodic knots/deltas and produce semantic beads:

- compress repeated evidence into stable concepts
- link semantic beads back to episodic evidence
- update confidence based on tests, repetition, and user/tool confirmation


