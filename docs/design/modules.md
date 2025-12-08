---
title: Elyra Module Catalogue
audience: Engineers and contributors
status: Planned design (no implementation yet)
last_updated: 2025-12-03
related_docs:
  - ./architecture.md
  - ../tech/memory-architecture.md
---

# Module Catalogue (v1 text-only, expandable per roadmap)

> **Status note**  
> This table describes the **intended module layout and target responsibilities**.  
> At the time of writing, this repository only contains documentation and stubs.

| Module                | Repo Path                     | Responsibility                              | Dependencies & Target Status |
|-----------------------|-------------------------------|---------------------------------------------|------------------------------|
| elyra-core            | /core                         | LangGraph supervisor for A2A, spawning, merging; multi-user routing. | LangGraph, FastAPI – Planned |
| hippocampal-sim       | /memory/hippocampal_sim       | Episodic buffer, EchoReplay (simulations), Hebbian tagger (plasticity), valence scorer. | PyTorch, Redis – Planned |
| graphiti-wrapper      | /memory/graphiti              | Bi-temporal KG CRUD, tiered queries, project sharding for multi-user. | Graphiti, Neo4j – Planned |
| camera-manager        | /sensory/camera_manager       | Active attention (look_at/look_around), YOLO/Eulerian integration (Phase 5). | OpenCV, Ultralytics – Planned |
| web-ui                | /ui (React + Tailwind)        | Multi-chat tabs, SSE for thoughts/memory/actions, KG visualization. | React, FastAPI – Planned |
| fastapi-gateway       | /api                          | Auth/sessions/SSE for multi-user; tool calls (browse_page et al.). | FastAPI, JWT – Planned |
| tools                 | /tools                        | Basics (browse_page, search); bootstrapper for LLM-gen customs (Phase 4). | LangChain, VeRL – Planned |
| ollama-client         | /llm                          | Wrapper for Mistral-7B remote; switchable to GPT-OSS (Llama 3.1). | Ollama API – Planned |
| daemon                | /daemon                       | Gap detection, proactive replay/reflection across users. | APScheduler – Planned |

## Expansion Notes

- **Phase 4**: Add VeRL (or similar) integration in `tools` for self-improvement of LLM-generated tools.
- **Phase 5**: `camera-manager` enables embodied sub-agents with active perception loops.
- **Cross-cutting**: All modules are designed to be LLM-agnostic; multi-user isolation is handled via `user_id` / `project_id` state and KG sharding.


