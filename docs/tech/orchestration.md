---
title: Orchestration – LangGraph, Agents, and State
audience: Engineers and contributors
status: Planned design + Phase 1 single-node MVP
last_updated: 2025-12-03
related_docs:
  - ../design/architecture.md
  - ./memory-architecture.md
  - ./tools-and-bootstrapping.md
---

## Overview

**Implementation status (Phase 1)**  
- The current codebase implements a **single-node** LangGraph workflow:
  - one `elyra` root node (no sub-agents yet),
  - simple per-session state (`ChatState`) carrying messages, ids, and a thought string.
- The multi-agent graph and richer state model described below are **design targets** for later phases.

Elyra’s orchestration layer uses **LangGraph** to wire together:

- the **Elyra root agent**,
- multiple **sub-agents** (Validator, Researcher, Planner, etc.),
- and system services (HippocampalSim, tools, daemon).

The goals are:

- clear, inspectable control flow,
- robust multi-agent collaboration,
- and built-in support for multi-user state.

## Core Graph Structure

- **Nodes**
  - `elyra_root`: central decision-maker.
  - `validator_sub`: checks factual consistency.
  - `researcher_sub`: calls web or API tools.
  - `planner_sub`: decomposes complex tasks.

- **Edges**
  - `START → elyra_root`
  - `elyra_root → validator_sub` (conditional)
  - `elyra_root → researcher_sub` (conditional)
  - `elyra_root → END` (when no further work is needed)

In early phases, the graph can be simple: a single `elyra` node with no subs, as shown in the conceptual `quickstart.py`.

## State Model

The shared state type (conceptual) looks like:

```python
from typing import Annotated, TypedDict, List
from langchain_core.messages import add_messages, BaseMessage


class ChatState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: str
    project_id: str
    scratchpad: str  # optional internal working notes
    tools_used: List[str]
```

Key points:

- Every node receives and returns a `ChatState`.
- `user_id` and `project_id` drive memory isolation and logging.
- `scratchpad` is for internal notes that may or may not be exposed to the user.

## Typical Turn Flow

1. **Entry**
   - Input arrives via FastAPI/WebSocket:
     - newest user message,
     - associated `user_id` and `project_id`.

2. **Root agent (elyra_root)**
   - Calls `hippocampal_sim.recall(...)` and `generate_thought(...)`.
   - Decides:
     - whether to call tools,
     - whether to delegate to sub-agents,
     - or whether to answer directly.

3. **Sub-agent calls (optional)**
   - Sub-agents receive the same `ChatState` plus any extra metadata.
   - They may:
     - call tools,
     - add intermediate messages,
     - annotate `scratchpad`.

4. **Merge and respond**
   - The root merges results from subs:
     - resolves conflicts using simple heuristics (e.g., prefer validated facts),
     - constructs a final response,
     - hands the response to the API layer for streaming.

5. **Ingestion**
   - The final response plus internal thoughts are passed back to HippocampalSim for storage.

## Multi-User Handling

- Each graph run is keyed by `(user_id, project_id)`.
- LangGraph’s state is:
  - logically isolated per session,
  - but can be resumed across WebSocket reconnects if desired.
- Daemon-like behaviours (replay, background thinking) run outside user-facing graphs but still operate per user/project.

## Daemon and Proactive Loops

- A separate process or scheduler:
  - periodically checks for idle periods,
  - triggers `hippocampal_sim.replay(...)` for active users/projects,
  - logs generated thoughts and memory updates.
- Optionally, these internal thoughts can generate:
  - notifications in the UI (e.g., “Elyra has been thinking about X…”),
  - or suggestions for the user’s next steps.

## HITL (Human-in-the-Loop) Controls

- **Breakpoints**
  - Certain nodes (e.g., dangerous tools, high-impact changes) can pause and wait for human approval.

- **Inspection**
  - Developers can inspect:
    - state snapshots,
    - intermediate messages,
    - tool invocations and results.

- **Override**
  - A reviewer can:
    - modify state,
    - reject a node’s output,
    - or force a different branch in the graph.

## Error Handling

- Node-level exceptions should:
  - be caught and translated into structured error messages,
  - update state (`tools_used`, `scratchpad`) with diagnostics,
  - trigger fallback paths when possible (e.g., ask the user for clarification).

- System should avoid “silent failure”:
  - log all exceptions centrally,
  - surface user-friendly messages when something goes wrong.

For tools and bootstrapping details, see `./tools-and-bootstrapping.md`.  
For the high-level diagram, see `../design/architecture_diagram.puml`.



