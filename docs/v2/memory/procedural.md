---
title: Procedural Memory (v2)
audience: Engineers and contributors
status: Draft (targeting implementation)
last_updated: 2025-12-25
related_docs:
  - ../README.md
  - ./episodic.md
  - ../architecture/braid-data-model.md
  - ../cognition/microagents.md
---

## Purpose

Procedural memory stores “how to do things”: tool beads, skill beads, playbooks, and microagent templates. Procedural memory is versioned, testable, and derived from episodic outcomes over time.

## What procedural memory stores

- **Tool beads**: callable operations (e.g., search, browse, code exec)
- **Skill beads**: multi-step procedures/templates that call tools and/or microagents
- **Microagent beads**: ephemeral agent templates (e.g., “run re-derivation test”)

## Versioning

Procedural beads are versioned and reusable:

- new versions are created when improvements are proposed
- prior versions remain addressable for audit and rollback

## Selection strategy (v0)

Procedural selection is layered:

1. retrieve candidates by semantic similarity to current topic/intent
2. rank by success frequency, recency, and trust
3. when off-topic feedback occurs, escalate to an LLM reviewer microagent to adjust weights and/or propose a fork pending


