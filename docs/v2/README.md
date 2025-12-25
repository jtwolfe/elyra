---
title: Elyra v2 (Braid) Documentation
audience: Engineers and contributors
status: Draft (targeting implementation)
last_updated: 2025-12-25
related_docs:
  - ../discussions/README.md
  - ../legacy/README.md
  - ../../submodules/README.md
---

## Elyra v2: Braid Architecture

Elyra v2 is a docs-first redesign where Elyra becomes a **composition layer** over:
- **LargeMemoryModel (LMM)**: episodic/semantic/procedural memory, beads, consolidation, retrieval
- **LargeCognitiveModel (LCM)**: knot processing (think/speak), microagents, tests, fork detection

This v2 documentation set is canonical. Legacy v1-era docs are preserved under `docs/legacy/`.

## Submodules (LMM/LCM)

The LMM and LCM repos are pinned in this repo under `submodules/` and should be initialized after cloning:

```bash
git submodule update --init --recursive
```

For update workflow, see `submodules/README.md`.

## Contents

- Architecture
  - `architecture/braid-overview.md`
  - `architecture/braid-data-model.md`
  - `architecture/runtime-and-scheduling.md`
  - `architecture/context-ribbon.md`
- Memory
  - `memory/episodic.md`
  - `memory/semantic.md`
  - `memory/procedural.md`
  - `memory/consolidation.md`
- Cognition
  - `cognition/microagents.md`
  - `cognition/tests-and-evaluation.md`
- UI
  - `ui/observability-and-ui.md`
- Migration
  - `migration/from-v1-to-braid.md`

