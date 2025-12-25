---
title: Elyra Overview & Goals
audience: Engineers and advanced users
status: Phase 1 MVP implemented with multi-agent orchestration
last_updated: 2025-12-10
related_docs:
  - ../design/project_intention.md
  - ../roadmap/roadmap.md
---
> **Legacy (superseded)**: This document is preserved for reference only. The canonical Braid v2 docs live in `docs/v2/`.



### What is Elyra?

Elyra is a **living, memory‑driven AI assistant** design: an LLM‑based agent wrapped in a rich, biologically‑inspired memory system.  
The goal is to get as close as possible to a **continuously consolidating, curiosity‑driven, autobiographical memory** for an AI agent, while still being usable on a laptop with plain text chat.

The long‑term design supports:
- **Deep memory**: Episodic and semantic memories stored in a temporal knowledge graph and vector store.
- **Proactive thinking**: Background “replay” and reflection when the user is idle.
- **Multi‑user & multi‑agent**: Multiple users, each with their own projects and sub‑agents.
- **Embodiment**: Optional camera/mic inputs that can be added later without rewriting the core.

At present, Elyra is both a **design and research blueprint** and a small **Phase 1 text‑only MVP** implementation.  
The code focuses on a minimal FastAPI + LangGraph backend, an in‑memory HippocampalSim stub, a tiny tool registry, and a React chat UI.

### Who are these docs for?

- **Primary**: Engineers and researchers who want to:
  - understand the intended architecture and memory model,
  - contribute code to a future implementation,
  - or adapt these ideas for their own systems.
- **Secondary**: Power users and collaborators who want to know what Elyra will eventually be able to do.

For non‑technical readers, start with this file and `design/project_intention.md`, and skip detailed tech docs on the first pass.

### Current status vs. planned system

- **Current repo state (Phase 1 MVP)**:
  - ✅ **Multi-agent LangGraph workflow**:
    - `planner_sub`: LLM-driven metacognitive planner for tool/agent selection
    - `researcher_sub`: Multi-shot research executor with iterative tool calls
    - `validator_sub`: Placeholder for future factual consistency checks
    - `elyra_root`: Final answer synthesis with tool execution
  - ✅ **FastAPI backend** with `/health` and WebSocket `/chat/{user_id}/{project_id}` endpoints
  - ✅ **In‑memory `HippocampalSim` stub**:
    - Context adequacy scoring (0.0-1.0) for intelligent research decisions
    - Dynamic thought generation
    - Optional JSON-backed persistence
  - ✅ **Tool Registry** with comprehensive baseline tools:
    - `web_search` (LangChain DuckDuckGoSearchRun)
    - `docs_search` (ChromaDB vector search with string fallback)
    - `browse_page`, `read_project_file`, `code_exec`, `get_time`
  - ✅ **React/Tailwind Web UI** with:
    - Chat interface
    - Debug panel showing `thought`, `tools_used`, `planned_tools`, `tool_results`, `scratchpad`
  - 📚 **Rich design docs** describing later phases (deep memory, replay, tool bootstrapping, embodiment)
- **Planned system** (beyond the current MVP):
  - Phase 2: Redis/Neo4j/Qdrant integration for persistent memory
  - Phase 3–4: Tool bootstrapping, LLM upgrade, self‑generated tools
  - Phase 5–6: Vision/audio inputs, richer simulations, production hardening

See `../roadmap/roadmap.md` for the phased plan and timelines, and `../init/overviewdocs.md` for a narrative overview of the architecture and phases.

### High‑level goals

- **Feel “alive” even in text‑only mode**  
  Elyra should generate internal thoughts, reflections, and memory recalls in the background, similar to human rumination.

- **Graceful embodiment**  
  The core should work without any sensors, but be able to use cameras/microphones later to ground memories in the physical world.

- **Multi‑user, multi‑agent by design**  
  Each user gets isolated projects and KGs, but agents can collaborate via shared subgraphs and sub‑agents.

- **Self‑improvement**  
  Elyra should eventually be able to propose, create, and refine its own tools (e.g., new LangChain tools) using code generation and RL‑style refinement.

### Non‑goals (v1)

- Full AGI or consciousness.
- Replacing enterprise agent platforms (CrewAI, Auto‑GPT, etc.) for classic business workflows.
- Requiring hardware from day one (cameras/mics are deferred to later phases).

### Where to go next

- For philosophy and high‑level intent, read `../design/project_intention.md`.
- For the system diagram and components, read `../design/architecture.md`.
- For the phased build‑out, read `../roadmap/roadmap.md`.
- For unfamiliar terms, check `../reference/glossary.md`.


