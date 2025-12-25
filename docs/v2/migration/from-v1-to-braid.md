---
title: Migration: v1 MVP to v2 Braid (Strip-out and Rebuild)
audience: Engineers and contributors
status: Draft (planning)
last_updated: 2025-12-25
related_docs:
  - ../README.md
  - ../architecture/braid-data-model.md
  - ../architecture/runtime-and-scheduling.md
  - ../../submodules/README.md
---

## Purpose

This document describes the planned migration from the current v1 MVP implementation in this repository to the v2 Braid architecture.

This is a **strip-out and rebuild**: we will keep what is useful for composition/UI/API, and replace memory + cognition internals with LMM/LCM.

## Current repo inventory (v1 MVP)

### Backend

- `elyra_backend/core/app.py`: FastAPI app + WebSocket chat endpoint
- `elyra_backend/core/state.py`: chat state model
- `elyra_backend/memory/hippocampal_sim/stub.py`: in-memory memory stub
- `elyra_backend/tools/registry.py`: tool registry
- `elyra_backend/llm/ollama_client.py`: Ollama client

### Frontend

- `ui/`: Vite + React UI (chat + debug panel)

### Tests

- `tests/`: pytest tests for current MVP components

## Replacement mapping (v2)

### What will be replaced

- Memory implementation (`hippocampal_sim` and related): replaced by **LargeMemoryModel (LMM)**.
- Knot processing / cognition orchestration: replaced by **LargeCognitiveModel (LCM)**.

### What will be kept (likely) as composition layer

- FastAPI/WebSocket surface (conceptually), updated to speak braid/knot semantics.
- UI shell, updated to render knots/deltas/beads/episodes.
- Minimal tool execution plumbing (re-homed behind LMM/LCM interfaces).

## Migration stages (recommended)

### Stage 0 — Docs canonicalization (done first)

- v2 docs become canonical (`docs/v2/`).
- legacy docs preserved and marked superseded (`docs/legacy/`).

### Stage 1 — Introduce LMM/LCM integration points (scaffolding)

- Add LMM/LCM as git submodules once those repos have an initial commit.
- Define python packaging/import boundaries (composition layer only).
- Introduce v2 interface shims in Elyra (no behavior change yet).

### Stage 2 — Implement braid log and minimal knot pipeline

- Replace the runtime flow to produce:
  - deltas
  - knots
  - thought summary beads
- Keep UI/API functional but minimal.

### Stage 3 — Replace memory/cognition internals

- Move episodic storage, semantic/procedural derivation, consolidators into LMM.
- Move knot think/speak orchestration + microagents/tests into LCM.

### Stage 4 — Remove v1 code

Remove v1-only modules once replacement coverage exists and tests are updated.

## Deletion criteria for v1 code

Before deleting a v1 module, ensure:\n- there is an equivalent v2 interface/implementation\n- observability is present (knot/delta traces)\n- test coverage exists for the new behavior\n- UI can inspect the new artifacts (knots/deltas/beads)\n

