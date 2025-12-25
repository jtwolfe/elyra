---
title: Runtime & Scheduling (v0)
audience: Engineers and contributors
status: Draft (targeting implementation)
last_updated: 2025-12-25
related_docs:
  - ../README.md
  - ./braid-data-model.md
  - ./context-ribbon.md
  - ../cognition/microagents.md
---

## Purpose

Define the v0 runtime model for Elyra Braid: knot aggregation cadence, think/speak passes, background metacognition, dreams, concurrency rules, and adaptive fork rate.

## Runtime loops (v0)

### Awake loops

- **Message loop**: user/perception inputs append deltas immediately. Message arrival during knot computation is recorded and handled in the next knot.
- **Knot loop**: commit knots on an aggregation window (baseline 30s), adaptive up/down.
- **Metacognition loop**: continuously (but budgeted) updates summaries, flags drift, schedules microagents/tests.
- **Consolidators** (memory workers): semantic/procedural consolidation runs on cadence and/or idle.

### Dream loop

Dreaming activates after extended idle. It generates draft hypotheses/deltas that decay unless reinforced.

Dream outputs must be distinguishable by provenance and default to low confidence.

## Knot aggregation and overload control

### Baseline cadence

- Baseline aggregation window: **30 seconds**.
- Aggregation is adaptive:
  - If knots consistently finish with slack, reduce window gradually.
  - If backlog grows or knots overlap, increase window.
  - When backlog clears, decay window back toward baseline.

### Concurrency rule

- Multiple knots may be queued.
- Only **one knot is allowed to commit at a time**.
- Background workers may continue producing deltas; any deltas arriving during a knot’s compute window are listed in `arrivals_during` and handled in the subsequent knot.

## Two-pass knot execution

### Think pass (internal)

Allowed:
- assemble context ribbon
- plan and execute tool calls
- spawn microagents
- propose/update hypotheses
- write memory deltas (episodic + derived)
- update summaries and trust

Not allowed:
- user-visible finalization requirements (speak is separate)

### Speak pass (user-facing)

Allowed:
- generate user response from current knot state + ribbon
- emit “I’m still thinking…” (when appropriate)

Not allowed:
- tool calls

### Budget overrun behavior

- If think-pass can’t finish within its budget, it may defer work to subsequent knots.
- For user-triggered interactions, the system should respond promptly, either with partial results + next steps or “I’m still thinking…” (and continue in background).

## Fork detection and fork rate control

### Pending-first forks

- Drift detection proposes `fork_pending` candidates (default top-3).
- Classifier confirms promotion to active.
- TTL defaults: **5–10 knots** and **10–20 minutes**.

### Conservative default

Default policy aims for fewer forks.

Fork aggressiveness adapts based on:
- fork confirmation rate
- auto-closed fork rate
- user “off-topic/not relevant” feedback
- rapid return-to-parent-topic rate


