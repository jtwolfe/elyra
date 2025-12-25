---
title: Context Ribbon (v0)
audience: Engineers and contributors
status: Draft (targeting implementation)
last_updated: 2025-12-25
related_docs:
  - ../README.md
  - ./braid-data-model.md
  - ./runtime-and-scheduling.md
---

## Purpose

Define how Elyra v2 assembles a **context ribbon** for each knot’s think/speak passes. The ribbon is reconstructed each knot from episodic + semantic + procedural memory (plus a short-term continuity buffer).

## Principles

- Rebuild context each knot from the most relevant information.
- Preserve continuity across forks by carrying a recent-message buffer plus anchors.
- Do not inject raw chain-of-thought into the ribbon by default.
- Include a narrative “I…” thought **summary bead** when useful.

## Inputs (high-level)

- Recent knots/messages (continuity buffer)
- Current episode summary (plus optional parent-echo)
- Summaries of other relevant episodes (and ability to expand)
- Semantic: relevant concepts/facts + confidence/contradictions
- Procedural: relevant tools/skills + success frequency
- Tool results from the current think-pass
## Exclusions (default)

- Raw/verbatim reasoning beads (unless explicitly requested or a debug mode is enabled)
- Large unfiltered episode logs
## Budgeting (placeholder)

Token budgets depend on model selection; target contexts may be large (e.g., ~50k). v0 should define a budget split, then tune with measurements.


