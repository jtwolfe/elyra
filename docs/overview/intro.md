---
title: Elyra Overview & Goals
audience: Engineers and advanced users
status: Design + Phase 1 text-only MVP
last_updated: 2025-12-03
related_docs:
  - ../design/project_intention.md
  - ../roadmap/roadmap.md
---

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

- **Current repo state**:
  - Minimal **Phase 1 text‑only MVP**:
    - FastAPI backend with `/health` and `/chat/{user_id}/{project_id}`.
    - Single‑node LangGraph workflow wrapping an Elyra root node.
    - In‑memory `HippocampalSim` stub (no Redis/Neo4j/Qdrant required).
    - Small `ToolRegistry` with a couple of built‑in tools.
    - React/Tailwind Web UI with chat + internal thought side panel.
  - Rich **design docs** describing later phases (deep memory, replay, multi‑agent orchestration, embodiment).
- **Planned system** (beyond the current MVP):
  - Text‑only MVP (Phase 1–2): Web UI, memory core, tools, and multi‑user support.
  - Scaling & tool bootstrapping (Phase 3–4): Multi‑agent orchestration, LLM upgrade, self‑generated tools.
  - Embodiment & optimization (Phase 5–6): Vision/audio inputs, richer simulations, production hardening.

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


