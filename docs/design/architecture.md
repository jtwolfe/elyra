---
title: Elyra Architecture Overview
audience: Engineers and advanced contributors
status: Planned design (no implementation yet)
last_updated: 2025-12-03
related_docs:
  - ../overview/intro.md
  - ./project_intention.md
  - ../roadmap/roadmap.md
---

# Architecture Overview – HippocampalSim v1 (text-only → embodied)

## High-Level Diagram

The system is modular: core memory (HippocampalSim) is LLM-agnostic, orchestration (LangGraph) handles agents, and front-ends (WebUI/API) support multi-user. Text-only mode bypasses sensory paths; embodiment adds streams without code changes.

The detailed sequence diagram lives in `architecture_diagram.puml` in this directory.

## Key Flows

- **User Interaction**: WebUI → API → LangGraph (Elyra root assesses query, spawns subs, merges).
- **Memory Cycle**: Input → Episodic Buffer → Tagging/Replay → KG Store → Recall for next cycle.
- **Proactive Mode**: Daemon polls gaps (text silence or motion) → Triggers reflection/replay.
- **Multi-User**: API sessions shard KG (e.g., user_id filters); shared subs for groups.
- **Tool Bootstrapping**: Elyra generates tools via LLM code-gen (Phase 4+), stored as KG nodes for reuse.

## Component Breakdown

- **User Interfaces**  
  React WebUI (Tailwind for styling) with chat tabs, memory viewer (KG graph render), thought bubbles (SSE for real-time), and action logs. Supports multi-user logins (e.g., JWT via FastAPI).

- **API Gateway**  
  FastAPI for auth/sessions/SSE; routes to LangGraph; handles multi-user concurrency (e.g., async queues for 50+ users).

- **Orchestration**  
  LangGraph for hierarchical graphs (root Elyra + subs); state includes `user_id` for isolation. Agent-to-agent communication via message edges; human-in-the-loop controls for approvals.

- **Memory Core (HippocampalSim)**  
  Bi-temporal KG (Graphiti on Neo4j) with tiers; EchoReplay (VAE/LSTM for simulations); Hebbian tagger (PyTorch for weights); emotional scorer (prosody/motion). Redis for episodic buffer/hot cache; Qdrant for vectors.

- **LLM Integration**  
  Ollama client (Mistral-7B remote); switchable to other open-source models (e.g., Llama 3.1 via HuggingFace in Phase 4).

- **Sensory Front-End**  
  Optional (added Phase 5); CameraManager for active switching; YOLO/Eulerian for vision; Whisper for speech-to-text.

- **Daemon**  
  APScheduler for proactive loops (gap detection → replay); runs in the background for all users.

- **Tools**  
  Start with basics (browse_page, search); bootstrap via code-gen (LangChain `StructuredTool` + VeRL for refinement).

## Scalability & Security

- **Horizontal scaling**: Kubernetes (or similar) for LangGraph pods; shard KG by user or project.
- **Fallback modes**: Text-only if no sensors; graceful degradation on LLM failures.
- **Privacy and “forgetting”**: Per-user KG filters; “forget” semantics implemented via temporal invalidation flags (e.g., `t_invalid`) rather than immediate hard deletes.

For more detail on the memory internals, see `../tech/memory-architecture.md`.  
For orchestration details, see `../tech/orchestration.md`.


