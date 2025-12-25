---
title: Braid Data Model & Contracts (v0)
audience: Engineers and contributors
status: Draft (targeting implementation)
last_updated: 2025-12-25
related_docs:
  - ../README.md
  - ./runtime-and-scheduling.md
  - ./context-ribbon.md
  - ../memory/episodic.md
  - ../discussions/README.md
---

## Purpose

Define the canonical **runtime contract** for the Braid architecture: **deltas**, **beads**, **knots**, **episodes**, **forks**, and **trust**. Implementations may vary (LangGraph vs custom runtime), but these invariants should remain stable.

## Core invariants (v0)

- **Append-only deltas**: All state changes are recorded as deltas.
- **Immutable knots**: A knot is an immutable checkpoint over a contiguous delta range, produced by cognition.
- **Episodes are overlays**: Episodes are overlapping groupings over knots/deltas. Every knot has a **primary episode**, and may be linked to others.
- **Forks are pending-first**: Topic/intent drift proposes a `fork_pending`; a classifier confirms promotion to active.
- **Two-pass knot**: A think-stage produces deltas; a speak-stage emits the user-facing response. Speak-stage **must not call tools**.
- **Dream is hypothesis-first**: Dream outputs are stored and can be recalled, but are treated as low-confidence hypotheses by default and decay unless reinforced.
- **Reasoning stored as beads**: Persist a narrative “I…” thought summary (and structured fields). Raw/verbatim CoT is optional behind a flag and never injected into context by default.

## Entity overview

### Identifiers

All identifiers are opaque strings (ULID/UUID recommended):

- `BraidID`
- `DeltaID`
- `BeadID` and `BeadVersionID`
- `KnotID`
- `EpisodeID`

### Provenance

Provenance is orthogonal to trust/confidence.

- `user`
- `assistant`
- `tool`
- `perception`
- `system`
- `dream`

## GenericDelta (storage envelope)

Everything is stored as a `GenericDelta`. `kind` defines the stable vocabulary; `payload` carries versioned, kind-specific data.

### DeltaKind (stable vocabulary, v0)

Minimum kinds:

- `tick`
- `message`
- `knot_lifecycle`
- `observation`
- `bead_ref`
- `bead_write`
- `bead_version`
- `tool_call`
- `tool_result`
- `microagent`
- `hypothesis`
- `trust`

### GenericDelta fields

Required:
- `id`: `DeltaID`
- `braid_id`: `BraidID`
- `kind`: `DeltaKind`
- `ts`: ISO-8601 timestamp
- `provenance`: `{ kind, source?, model?, tool?, episode_id?, knot_id? }`
- `confidence`: float in `[0, 1]`
- `payload`: JSON object (versioned per `kind`)

Optional:
- `refs`: `{ beads?: [BeadRef], knots?: [KnotID], episodes?: [EpisodeID], deltas?: [DeltaID] }`
- `tags`: `[string]`

### BeadRef

- `bead_id`: `BeadID`
- `bead_version_id`: optional (if omitted, means “active version at time of knot”)
- `role`: e.g. `used`, `created`, `updated`, `proposed`, `tested`, `evidence`

## Beads (artifacts in memory)

Beads are addressable artifacts stored in memory and referenced by deltas and knots. Beads are **versioned** and reusable.

### BeadType (v0)

- `tool_bead`: callable tool (e.g. `web_search`)
- `skill_bead`: procedure/template (e.g. a multi-step workflow)
- `memory_bead`: semantic/procedural/episodic artifact (e.g. summary, hypothesis, quote set)
- `microagent_bead`: ephemeral agent template/spec
- `reasoning_bead`: thought summaries; optional raw CoT behind a flag

### Versioning rules

- Beads are *logically updatable* through versioning:
  - “Update bead” means create a new `BeadVersion` and record a delta pointing to the new active version.
- Old versions remain addressable for audit and replay.

## Knots

### Definition

A knot is an immutable checkpoint produced by cognition over a delta range. Knots are **state slices**, primarily capturing memory state and the outputs of cognition.

### Required knot fields (v0)

- `id`: `KnotID`
- `braid_id`: `BraidID`
- `primary_episode_id`: `EpisodeID` (always set; default “session @ timecode” episode if unknown)
- `delta_range`: `{ start_delta_id, end_delta_id }`
- `start_ts`, `end_ts`
- `inbox_watermark`: what inputs were visible at knot start
- `arrivals_during`: list of input delta IDs (messages/observations) that arrived while this knot was being computed
- `summary`: short human-readable summary
- `thought_summary_bead_ref`: `BeadRef` to a `reasoning_bead` version (narrative “I…” + structured fields)
- `planned_tools`: planned tool calls (even if not executed)
- `executed_tools`: refs to executed `tool_result` deltas/beads
- `hypotheses`: refs to hypothesis/test deltas/beads touched this knot
- `metrics`: `{ latency_ms, token_estimate, fork_pending_count, ... }`

### Two-pass semantics

- **Think pass**: may create deltas (tools, hypotheses, memory writes, summaries).
- **Speak pass**: emits user response delta. No tool calls allowed.

## Episodes

### Definition

Episodes are overlapping overlays grouping knots/deltas by time/topic/intent. Episodes can overlap and reference each other.

### Required episode fields (v0)

- `id`: `EpisodeID`
- `braid_id`: `BraidID`
- `labels`: `{ topics: [string], intents: [string], modalities: [string] }`
- `primary_knot_span`: `{ start_knot_id?, end_knot_id? }`
- `knot_refs`: `[KnotID]` (additional membership)
- `edges`: list of `{ type, to_episode_id, confidence }`
- `summary_cache`: cached summary (cheaply updated; may be improved by background LLM worker)
- `anchor_quotes`: 2–5 quote objects selected by weights (constraints/decisions/open_questions = 70/20/10)

### Episode edges (v0)

- `related_to`
- `forked_from`
- `resumed_from`
- `soft_link`
- `contradicts`
- `depends_on`

## Forks and drift handling

### Fork lifecycle (pending-first)

1. Drift signals propose `fork_pending` episode(s) (top-K candidates; default K=3).
2. A classifier confirms or rejects.
3. Default policy is conservative (fewer forks), adaptively tuned.

### TTL defaults

- `fork_pending` TTL: **5–10 knots** and **10–20 minutes** (whichever hits first).
- On expiry without confirmation: decay to `soft_link` or discard.

### Continuity buffer across forks

When a fork becomes active, the new episode retains a reduced continuity buffer:

- **recent messages**: ~15–30 messages (or last 5–10 minutes of knots)
- **summary**: a compact “what we were doing / goal / unresolved”
- **anchor quotes**: 2–5 quotes

## Trust model

### Goals

- Allow **strand-local trust** while maintaining a **global baseline** for the system.
- Treat dream-origin content as low-confidence by default, without forbidding promotion.

### Minimal trust fields (v0)

- `confidence`: `[0..1]`
- `decay_policy`: (optional) time-based and/or usage-based
- `promotion_rules`: (optional) tests required to promote
- `provenance`: required (e.g., dream vs tool vs user)

## Hypotheses and tests (v0 hooks)

Hypotheses are first-class and can be tested before promotion.

Minimum MVP-safe tests:
- Consistency (no contradiction with high-confidence semantic)
- Re-derivation (reproduce via microagent)
- Outcome (reward/user feedback)

Tool grounding tests are best-effort and depend on available tools.


