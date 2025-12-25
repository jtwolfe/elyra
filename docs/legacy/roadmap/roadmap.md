---
title: Elyra Roadmap – From MVP to Feature-Complete Assistant
audience: Engineers, contributors, and project leads
status: Planned design (no implementation yet)
last_updated: 2025-12-03
related_docs:
  - ../overview/intro.md
  - ../design/project_intention.md
  - ../design/architecture.md
---
> **Legacy (superseded)**: This document is preserved for reference only. The canonical Braid v2 docs live in `docs/v2/`.



# Comprehensive Roadmap for Elyra

This roadmap lays out how Elyra should evolve from a **text-only MVP** into a **feature-complete, self-improving, embodied assistant**.
It assumes a small team (1–3 devs) working part-time; adjust timelines for your actual resources.

- **Target start window**: December 2025 – January 2026.
- **Expected duration**: 6–12 months (roughly Q1–Q4 2026).

Throughout, remember that this is a **design roadmap**: the current repository contains documentation and plans, not a working system.

## Research Synthesis Guiding the Roadmap

- **Neuroscience-Inspired Memory Roadmaps**  
  2025-style literature emphasises phased development: conceptual design (e.g., “infinite memory” via hierarchical KGs), prototyping (unified neuroscience–AI bridges), integration (multi-agent collaboration), and testing (temporal benchmarks such as LongMemEval). Hardware roadmaps (e.g., neuromorphic work) suggest starting software-only, then layering on hardware-accelerated components later.

- **Open-Source GPT Alternatives**  
  Modern open-source models (e.g., Llama 3.x, Mistral families, Qwen, DeepSeek) provide strong reasoning and tool-use abilities. Early phases can run on smaller models (e.g., 7–12B via Ollama), upgrading to larger models (e.g., 70B+) in later phases when tool bootstrapping becomes central.

- **LangChain Custom Tools & Bootstrapping**  
  LangChain supports dynamic tools via decorators and `StructuredTool` definitions. Best practices emphasise robust error handling, async execution, and reflective patterns (agents critique and improve their own tool calls). For bootstrapping, we borrow ideas from ToolGen-style encodings and agent frameworks that let LLMs propose new tools under human review.

- **Embodied AI Frameworks with Multi-Agent**  
  Recent embodied multi-agent work explores collaborative navigation, manipulation, and shared environments. Frameworks like OpenVLA and multi-agent coordination toolkits inform how Elyra can eventually extend from text-only to sensorimotor scenarios (camera/mic inputs, robot sims).

- **Bootstrapping Self-Improving Agents**  
  Research on tool-augmented LLMs and self-improvement (e.g., course notes like Stanford CS329A, “coding agents” discussions, RL-style refinement loops) shapes Elyra’s later phases. The key pattern: agents generate candidate tools or code, evaluate those tools on tasks, then refine them via feedback or RL (e.g., VeRL-like, low-data RL).

## Roadmap Overview

- **Total Duration**: 6–12 months (Q1–Q4 2026), assuming part-time effort.
- **Assumptions**:
  - Start with text-only Mistral-7B (or similar) on a remote Ollama host.
  - Switch to a stronger OSS model (e.g., Llama 3.x) in Phase 4 for better reasoning and tool creation.
  - Tools begin as a small, curated set (browse_page, search, etc.), then grow via LLM-generated tools.
  - Multi-user handled via FastAPI sessions and a WebUI.
- **Risks**:
  - LLM hallucinations during tool creation or planning.
  - Overly ambitious hardware/embodiment scope.
  - Operational complexity (Kubernetes, GPUs) for small teams.
- **Mitigations**:
  - Human-in-the-loop (HITL) approvals for new tools.
  - Strong observability and evaluation (e.g., LangSmith-like tracing and tests).
  - Clear separation between “experimental” and “production” tools/agents.
- **Metrics**:
  - Phase success based on benchmarks: LongMemEval for memory, HumanEval-style tests for tool correctness, and custom multi-user simulations for coordination.
  - High-level success metrics in `../design/project_intention.md` map directly onto these phases (Phase 1, 4, and 6).

### Phase Table

| Phase | Timeline | Dependencies | Key Features & Milestones | Notes & Rationale |
|-------|----------|--------------|---------------------------|-------------------|
| **1: MVP – Text-Only Foundation** | Weeks 1–4 (Q1 2026) | `quickstart.py` design, Mistral-7B via Ollama, LangGraph, Graphiti/Neo4j/Redis/Qdrant | - WebUI (React+Tailwind): Chat, thought/memory/action streams (SSE for real-time).<br>- Basic Elyra: Root agent + 2–3 subs (e.g., Validator, Researcher).<br>- Memory: Bi-temporal KG with tiers, basic recall (no replay yet).<br>- Tools: 5–10 basics (browse_page, search, code_exec).<br>- Multi-User: FastAPI sessions (isolated KG views).<br>- **Milestone**: Elyra responds to 2 users concurrently, showing thoughts and relevant memories. | Start with core orchestration and basic memory before adding proactive replay or embodiment. |
| **2: Proactive Memory & Reflection** | Weeks 5–8 | Phase 1, PyTorch for ML modules | - Add EchoReplay (VAE/LSTM for simulations) and Hebbian tagger (weight updates).<br>- Daemon: Gap-triggered reflection (e.g., 15 min idle → consolidate tiers).<br>- Multi-Agent: Implicit/explicit spawning (LangGraph nodes); agent-to-agent merging with simple heuristics.<br>- WebUI: Render KG subsets and thought bubbles.<br>- **Milestone**: Elyra “thinks” proactively in downtime and evolves sub-agent behaviours via replay. | Core “aliveness” features; influenced by neuroscience consolidation and self-improving agent research. |
| **3: Multi-User/Multi-Agent Scaling** | Weeks 9–12 | Phase 2, optional Kubernetes/Docker Swarm | - Full multi-user: Per-project KG shards, shared subgraphs for groups.<br>- Advanced A2A: Parallel subs with valence/reward-based merging.<br>- Tools Expansion: ~20 tools (APIs, web_search); initial bootstrapping (LLM generates simple tools from templates).<br>- WebUI: Multi-chat tabs and user dashboards for memory/agents.<br>- **Milestone**: Elyra handles 5 users + 10 subs concurrently, and bootstraps at least one simple tool on-the-fly. | Stress-tests concurrency and coordination before involving sensors or larger models. |
| **4: LLM Upgrade & Tool Bootstrapping** | Months 4–6 (Q2) | Phase 3, access to a stronger GPU or cloud LLM | - Switch to a more capable OSS model (e.g., Llama 3.x 70B via Ollama/HuggingFace or similar).<br>- Full bootstrapping: Elyra generates tools (LangChain `StructuredTool` + code-gen); self-improves via VeRL-like, low-data RL for tool refinement.<br>- Evaluations: Use tracing/eval tooling to measure tool success (e.g., 90%+ pass rate on a HumanEval-style task set).<br>- **Milestone**: Elyra creates/optimizes at least 5 custom tools autonomously (e.g., “Build a weather checker”). | Stronger LLMs unlock more reliable tool generation and planning; this phase is about making the system self-extensible. |
| **5: Embodiment & Multimodality** | Months 7–9 (Q3) | Phase 4, camera/mic hardware | - Add `CameraManager` (active camera switching, view selection) with YOLO/Eulerian-based motion/valence signals.<br>- Multimodal fusion: Integrate CLIP-/Whisper-style embeddings into the episodic buffer; sub-agents can “see/hear” independently.<br>- Mirror-Neuron Behaviours: Sub-agents clone patterns from video/audio (e.g., demonstration-based imitation).<br>- WebUI: Render camera feeds, visual valence overlays, and multimodal memory snippets.<br>- **Milestone**: Elyra supports embodied multi-user sessions (e.g., “Look at the office cam during group chat and remember this meeting”). | This phase ties the neuroscientific inspiration to real-world sensory data. |
| **6: Feature-Complete & Optimization** | Months 10–12 (Q4) | All prior phases, plus cloud scaling | - Advanced bootstrapping: Elyra iteratively improves tools via RL (VeRL integration) and self-optimises KG structure (e.g., pruning or merging via replay).<br>- Full multi-user collaboration: Shared sub-agents, branching/forking project memories, and access control on shared KGs.<br>- Production rollout: Kubernetes deployment, strong monitoring/alerts, and evaluation suites (LongMemEval, HumanEval-style tests, multi-user scenarios).<br>- **Milestone**: Elyra has 20+ tools (including self-generated ones), handles ~50 concurrent users, and runs in at least one embodied robot or simulator environment. | The “living system” phase: focus on robustness, safety, and continuous self-improvement rather than new features. |

## Relationship to Success Metrics

High-level success metrics in `../design/project_intention.md` are tied to this roadmap:

- **Phase 1** → LongMemEval recall targets in a text-only setting.
- **Phase 4** → HumanEval-style success rates for autonomous tool creation.
- **Phase 6** → Multi-user embodied simulation accuracy and robustness metrics.

These metrics should be tracked via automated evaluation suites and surfaced in dashboards as the implementation progresses.


