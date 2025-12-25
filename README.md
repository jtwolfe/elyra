## Elyra (Braid v2)

Elyra is an agent system being built around a **Braid** architecture: an append-only stream of **deltas** with periodic immutable checkpoints (**knots**), with overlapping narrative/topic groupings (**episodes**), and addressable artifacts (**beads**).

In this repository, “v2” is implemented as a **composition layer** over two submodules:

- **LargeMemoryModel (LMM)**: episodic store, braid schema, ribbon building primitives
- **LargeCognitiveModel (LCM)**: two-pass knot processing (think/speak), fork detection hooks, MVP-safe tests

### Documentation

- **Canonical Braid v2 docs**: `docs/v2/README.md`
- **Discussion imports / research notes**: `docs/discussions/README.md`
- **Legacy v1 docs (superseded)**: `docs/legacy/README.md`

### Current state (what works today)

The project is **runnable** end-to-end (backend + UI) and implements a testable subset of the v2 design:

- **Backend**: FastAPI + WebSocket chat (`WS /chat/{user_id}/{project_id}`)
- **Frontend**: React + Vite dev UI with:
  - chat panel
  - “Internal state” panel
  - **Inspector** tab (polls `/inspect/{user_id}/{project_id}/snapshot`)
  - **Reset all** button (dev-only, requires typing `reset`)
- **Two-pass cognition**:
  - **think-pass** produces structured JSON including `microagent_request`
  - **speak-pass** produces the user response (no tool calls allowed)
- **Microagent-first tool execution (no bypass)**:
  - tools exist as **`tool_bead`s**
  - tool use occurs only via a **microagent runner** which writes auditable deltas:
    - `DeltaKind.microagent`
    - `DeltaKind.tool_call` / `DeltaKind.tool_result` including refs to the microagent bead + tool bead
- **Persistence**:
  - **Neo4j** episodic store backend (optional; `ELYRA_PERSISTENCE_BACKEND=neo4j`)
  - **Qdrant** semantic recall (optional; `ELYRA_ENABLE_QDRANT=1`)
    - per-braid collection naming: `elyra_semantic_{user}_{project}`
    - indexes semantic turn summaries and retrieves top‑K relevant items into the ribbon
- **Data isolation**:
  - Neo4j bead version queries are **braid-scoped** to avoid cross-braid contamination
- **Tests**:
  - unit tests for chat flow, fork lifecycle basics, trust scoring scaffolding
  - opt-in integration tests for Neo4j/Qdrant

### What is *not* complete yet (remaining work to align with full v2)

This repo is intentionally still a “v2 skeleton”: the core contracts are in place, but many v2 features are simplified.

#### P0/P1 correctness & safety hardening

- [ ] **Secret management**: move dev defaults (e.g. Neo4j password) to `.env` patterns + provide `.env.example`
- [ ] **Stronger prompt-injection defenses**: explicit untrusted context framing + tool result sanitization + policy tests
- [ ] **Auth/authorization**: secure admin endpoints (reset) and protect inspector endpoints in non-dev deployments

#### Braid model completeness

- [ ] **Episodes as first-class overlays** across UI/engine (beyond the current minimal “active episode” + a tools overlay)
- [ ] **Forks**: richer fork proposal/confirmation UX, continuity snapshots, and better TTL semantics
- [ ] **Bead taxonomy & schemas**: formalize bead types/data models for microagents, tools, skills, procedures

#### Microagents (beyond MVP)

- [ ] **Multi-step microagent loops** (plan → tool → reflect → tool …) with budgets and stopping criteria
- [ ] **Tool permissioning**: tool-bead allowlists per episode/thread; provenance-based trust constraints
- [ ] **Microagent thread ownership**: “tools usable via micro-agents that come from a specific thread in the braid”
      should be expanded from “single tools overlay episode” to explicit per-task/per-thread microagent episodes

#### Memory and retrieval alignment

- [ ] **Semantic/procedural consolidation workers** (beyond the current minimal semantic indexing)
- [ ] **Trust model**: broaden evidence inputs (tool reliability, contradictions, decay, provenance weighting)
- [ ] **Richer Qdrant schema**: store embeddings for more delta kinds (tool calls/results, facts, procedures), plus filters

#### Productionization

- [ ] **Deployment story** (compose profiles, health checks, migrations, schema management)
- [ ] **Observability** (structured logging, tracing, metrics; inspector should not be the only introspection tool)

### Quickstart (dev)

See `DEVELOPMENT.md` and `RUNNING_LOCALLY.md`. Typical flow:

1) Start infra (Neo4j + Qdrant):

```bash
podman-compose up -d  # or: docker compose up -d
```

2) Backend:

```bash
cd /home/jim/Workspace/elyra
source .venv/bin/activate

export ELYRA_LLM_BACKEND=ollama
export ELYRA_OLLAMA_MODEL="gpt-oss:latest"
export ELYRA_OLLAMA_BASE_URL_PRIMARY="https://hyperion-ollama.threshold.houseofdata.dev/"
export ELYRA_OLLAMA_BASE_URL_FALLBACK="https://ollama.threshold.houseofdata.dev/"

export ELYRA_PERSISTENCE_BACKEND=neo4j
export ELYRA_NEO4J_URI="bolt://localhost:7687"
export ELYRA_NEO4J_USER="neo4j"
export ELYRA_NEO4J_PASSWORD="password"   # dev default; change for real deployments

export ELYRA_ENABLE_QDRANT=1
export ELYRA_QDRANT_URL="http://localhost:6333"

export ELYRA_ENABLE_WEB_SEARCH=0
export ELYRA_ENABLE_DANGEROUS_ADMIN=1    # enables Reset All (dev-only)

uvicorn elyra_backend.core.app:app --host 0.0.0.0 --port 8000
```

3) UI:

```bash
cd /home/jim/Workspace/elyra/ui
npm install
npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
```

Open `http://localhost:5173`.


