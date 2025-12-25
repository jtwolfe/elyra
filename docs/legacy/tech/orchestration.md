---
title: Orchestration – LangGraph, Agents, and State
audience: Engineers and contributors
status: Phase 1 MVP - Multi-agent graph implemented
last_updated: 2025-12-10
related_docs:
  - ../design/architecture.md
  - ./memory-architecture.md
  - ./tools-and-bootstrapping.md
---
> **Legacy (superseded)**: This document is preserved for reference only. The canonical Braid v2 docs live in `docs/v2/`.



## Overview

**Implementation status (Phase 1)**  
- The current codebase implements a **multi-agent LangGraph workflow**:
  - `planner_sub`: LLM-driven metacognitive planner that decides tool usage and agent delegation
  - `researcher_sub`: Multi-shot research executor capable of iterative tool calls and retries
  - `validator_sub`: Placeholder for future factual consistency checks
  - `elyra_root`: Final answer synthesis node that executes planned tools and generates user-facing responses
  - `ChatState` includes routing decisions, planned tools, tool results, and dynamic thought tracking
- The graph structure matches the planned architecture, with LLM-driven planning replacing brittle keyword-based triggers.

Elyra’s orchestration layer uses **LangGraph** to wire together:

- the **Elyra root agent**,
- multiple **sub-agents** (Validator, Researcher, Planner, etc.),
- and system services (HippocampalSim, tools, daemon).

The goals are:

- clear, inspectable control flow,
- robust multi-agent collaboration,
- and built-in support for multi-user state.

## Core Graph Structure

**Current Implementation (Phase 1)**

- **Nodes**
  - `planner_sub`: **IMPLEMENTED** - LLM-driven metacognitive planner that analyzes context, decides tool usage, and routes to sub-agents
  - `researcher_sub`: **IMPLEMENTED** - Multi-shot research executor that iteratively calls tools (docs_search, web_search, browse_page, read_project_file) with retry logic
  - `validator_sub`: **PLACEHOLDER** - Pass-through node for future factual consistency checks
  - `elyra_root`: **IMPLEMENTED** - Executes planned tools, synthesizes final answers, ingests results to memory

- **Edges**
  - `START → planner_sub` (always first)
  - `planner_sub → researcher_sub` (if `route="researcher"`)
  - `planner_sub → validator_sub` (if `route="validator"`)
  - `planner_sub → elyra_root` (if `route="end"` or default)
  - `researcher_sub → elyra_root` (always, after research completes)
  - `validator_sub → elyra_root` (always, after validation)
  - `elyra_root → END` (final node)

**Key Design Decision**: The planner runs first on every turn, making LLM-driven decisions about tool usage and agent delegation. This replaces brittle keyword-based triggers with intelligent metacognition.

## State Model

**Current Implementation** (`elyra_backend/core/state.py`):

```python
class ChatState(TypedDict):
    messages: List[BaseMessage]
    user_id: str
    project_id: str
    thought: str  # Dynamic per-turn thought (from LLM <think> or HippocampalSim)
    tools_used: List[str]  # Names of tools invoked this turn
    scratchpad: str  # Internal notes for debugging/routing
    route: str | None  # Planner's routing decision: "researcher", "validator", "end"
    planned_tools: List[Dict[str, Any]]  # Planner's requested tools: [{"name": str, "args": dict}]
    tool_results: List[Dict[str, Any]]  # Actual tool execution results
```

Key points:

- Every node receives and returns a `ChatState`.
- `user_id` and `project_id` drive memory isolation and logging.
- `route` is set by `planner_sub` to control graph flow.
- `planned_tools` and `tool_results` enable tool execution tracking and observability.
- `thought` is dynamically updated per turn (from LLM reasoning blocks or HippocampalSim).
- `scratchpad` accumulates internal notes across nodes for debugging.

## Typical Turn Flow

**Current Implementation (Phase 1)**:

1. **Entry**
   - Input arrives via FastAPI/WebSocket:
     - newest user message,
     - associated `user_id` and `project_id`.
   - Initial `ChatState` constructed with empty `planned_tools`, `tool_results`, `route=None`.

2. **Planner sub-agent (`planner_sub`)** - **ALWAYS RUNS FIRST**
   - Calls `hippocampal_sim.recall(...)` to get context and **context adequacy score** (0.0-1.0).
   - LLM analyzes:
     - user query,
     - memory context and adequacy signal,
     - available tools catalog (`ToolRegistry.list_tools()`),
     - available sub-agents (researcher, validator, elyra_root).
   - LLM outputs structured plan in `<plan>...</plan>` JSON:
     - `delegate_to`: "researcher" | "validator" | "end"
     - `tools`: [{"name": str, "args": dict}]
   - Updates `state["route"]`, `state["planned_tools"]`, `state["thought"]`, `state["scratchpad"]`.
   - **Key innovation**: LLM-driven metacognition replaces keyword triggers.

3. **Router (`_elyra_router`)**
   - Reads `state["route"]` set by planner.
   - Routes to: `researcher_sub`, `validator_sub`, or `elyra_root` (end).

4. **Sub-agent execution (conditional)**
   - **`researcher_sub`** (if routed):
     - Multi-shot loop (up to `RESEARCHER_MAX_ITERATIONS`):
       - Iteration 0: `docs_search` (for project docs)
       - Iteration 1: `web_search` (for external info)
       - Iteration 2+: `browse_page` (if URLs found) or retries
     - Retries if results insufficient (`RESEARCHER_MIN_RESULTS_THRESHOLD`).
     - Builds comprehensive summary from all tool results.
     - Updates `state["tool_results"]`, `state["tools_used"]`, `state["scratchpad"]`.
   - **`validator_sub`** (if routed):
     - Placeholder pass-through (Phase 1).

5. **Root agent (`elyra_root`)**
   - Executes any tools in `state["planned_tools"]` (if not already executed by researcher).
   - Calls `hippocampal_sim.recall(...)` and `generate_thought(...)`.
   - Ingests tool results into memory as synthetic `AIMessage`s.
   - Constructs system prompt with:
     - memory context,
     - internal thought,
     - tool outputs summary.
   - Calls LLM to generate final user-facing answer.
   - Parses `<think>...</think>` for dynamic `thought`.
   - Ingests final response to memory.

6. **Response**
   - Returns `ChatState` with:
     - final `AIMessage`,
     - `thought` (dynamic per-turn),
     - `tools_used`, `planned_tools`, `tool_results` (for UI trace),
     - `scratchpad` (for debugging).
   - WebSocket streams response to frontend.

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

**Current Implementation**:

- **Planner errors**:
  - Parsing failures logged with raw LLM response for debugging.
  - Fallback JSON extraction using regex if `<plan>` tags missing.
  - Invalid `delegate_to` values default to "end".
  - Tool specification errors logged and skipped.

- **Researcher errors**:
  - Tool execution failures logged with error details.
  - Retries with alternative tools if results insufficient.
  - Maximum iterations reached logged as warning.
  - Partial results returned if all tools exhausted.

- **Root agent errors**:
  - Tool execution failures logged, execution continues.
  - Memory ingestion failures logged but non-blocking.
  - LLM response parsing failures fall back to raw response.

- **Comprehensive error messages**:
  - All sub-agents log structured error messages (see `tools-and-bootstrapping.md`).
  - Errors update `scratchpad` for UI visibility.
  - System avoids silent failures with defensive logging throughout.

For tools and bootstrapping details, see `./tools-and-bootstrapping.md`.  
For the high-level diagram, see `../design/architecture_diagram.puml`.



