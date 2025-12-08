---
title: Elyra Documentation
audience: Engineers and advanced users
status: Design blueprint (no implementation yet)
last_updated: 2025-12-03
related_docs:
  - overview/intro.md
  - design/project_intention.md
  - roadmap/roadmap.md
---

### Elyra Documentation Overview

Elyra is currently a **design and architecture blueprint** for a living, memory‑driven AI assistant.  
This repository does not yet contain a full implementation; the docs describe the **target system**.

- **Start here**
  - `overview/intro.md` – plain‑English overview, goals, and non‑goals.
  - `roadmap/roadmap.md` – phased plan from text‑only MVP to embodied, self‑improving system.
- **Core design docs**
  - `design/project_intention.md` – intention, vision, goals, non‑goals, success metrics.
  - `design/architecture.md` – high‑level architecture, components, and flows.
  - `design/theory_of_mind.md` – neuroscience ↔ AI mapping and mental model.
  - `design/modules.md` – intended module layout and responsibilities.
- **Technical deep dives**
  - `tech/memory-architecture.md` – HippocampalSim, episodic buffer, KG, vectors.
  - `tech/llm-stack.md` – LLM choices, Ollama integration, prompting.
  - `tech/orchestration.md` – LangGraph graphs, multi‑agent orchestration, state.
  - `tech/tools-and-bootstrapping.md` – tools, self‑generated tools, VeRL/ToolGen‑style loops.
  - `tech/embodiment.md` – camera/audio stack and multimodal fusion.
  - `tech/evaluation-and-monitoring.md` – benchmarks and monitoring.
- **Reference & meta**
  - `reference/glossary.md` – definitions of recurring concepts and technologies.
  - `reference/api-reference.md` – placeholder for future API reference.
  - `meta/docs_contributing.md` – how to extend and maintain the docs.

### Getting Started for Contributors

- **1. Read the high-level docs**
  - `overview/intro.md` – what Elyra is, who it’s for, and current status.
  - `design/project_intention.md` – vision, goals, and success metrics.
  - `roadmap/roadmap.md` – phased plan and where we are in it.

- **2. Skim the architecture**
  - `design/architecture.md` and `design/architecture_diagram.puml` – main components and flows.
  - `tech/memory-architecture.md` and `tech/orchestration.md` – how memory and agents tie together.

- **3. Choose an area to help with**
  - **Docs-only**: clarify or extend any design/tech doc; follow `meta/docs_contributing.md`.
  - **Future code**: pick a roadmap phase and module from `design/modules.md` and start drafting designs or stubs in a separate branch/repo.

- **4. Open an issue or PR**
  - Describe what you’re changing (docs vs design vs future implementation).
  - Link the most relevant design and roadmap docs so reviewers have context.


