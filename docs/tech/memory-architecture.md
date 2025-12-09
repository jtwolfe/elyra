---
title: Memory Architecture – HippocampalSim
audience: Engineers and researchers
status: Planned design + in-memory Phase 1 stub
last_updated: 2025-12-03
related_docs:
  - ../design/architecture.md
  - ../design/theory_of_mind.md
  - ./orchestration.md
---

## Overview

**Implementation status (Phase 1)**  
- The current implementation in `elyra_backend/memory/hippocampal_sim/stub.py` is a **purely in-memory stub**:
  - keeps a short list of recent assistant messages per `(user_id, project_id)`,
  - returns a trivial text context from these episodes,
  - generates a fixed internal thought string,
  - does not talk to Redis, Neo4j, or Qdrant yet.
- The richer architecture described below (episodic buffer, temporal KG, vector store, replay, Hebbian tagger, valence) is a **future target**.

HippocampalSim is Elyra’s memory core. It provides:

- an **episodic buffer** for recent events,
- a **bi-temporal knowledge graph** for long-term, structured memory,
- a **vector store** for dense semantic retrieval,
- **replay and simulation** (EchoReplay),
- and **plasticity mechanisms** (Hebbian tagger, valence scorer).

The LLM never sees raw history; it sees a *curated slice* assembled by HippocampalSim on each turn.

## Data Stores

- **Redis (Episodic Buffer)**
  - Stores short-lived episodes (dialogue turns, tool results, sensor snippets).
  - Organised by `(user_id, project_id)` with TTLs to keep the buffer small.
  - Acts as the source for replay sampling and recent-context stitching.

- **Graphiti + Neo4j (Temporal KG)**
  - Graphiti provides a temporal KG abstraction over Neo4j (or another graph DB).
  - Nodes represent entities (users, tasks, locations, objects, concepts).
  - Edges represent relations tagged with:
    - valid time (`t_valid_from`, `t_valid_to`),
    - transaction time (`t_tx_from`, `t_tx_to`),
    - visibility and privacy flags (per user/project).
  - Supports queries like:
    - “What were the last 5 tasks we worked on for this project?”
    - “What did the user believe about X last week?”

- **Qdrant (Vector Store)**
  - Stores embeddings of:
    - user messages,
    - tool outputs and documents,
    - summaries of episodes or scenes.
  - Indexed per `(user_id, project_id, modality)` for isolation and filtering.
  - Used to surface semantically related memories when KG structure is insufficient.

## Episodic Flow

1. **Ingest**
   - Each user interaction (and tool result) is wrapped into an `Episode` object:
     - raw content (text, metadata, optional embeddings),
     - timestamps,
     - high-level tags (topic, valence, modality).
   - Episodes are written to Redis and batched to:
     - Graphiti/Neo4j (as nodes/edges),
     - Qdrant (as vector points).

2. **Recall**
   - Given a new user message, HippocampalSim:
     - queries Redis for very recent episodes in this session,
     - queries Graphiti for structurally related memories,
     - queries Qdrant for semantically similar items,
     - merges and deduplicates results,
     - summarises them into a compact **context block** for the LLM.

3. **Consolidation & Pruning**
   - Background jobs periodically:
     - compress low-value episodes into summaries,
     - mark edges or nodes as invalid via `t_invalid` flags,
     - promote frequently accessed edges into higher-priority tiers.

## Research Outputs and Memory Integration

Tool-based research (e.g., `docs_search`, `web_search`, `browse_page`, `read_project_file`) produces information that should be treated as **first-class episodes** and, in some cases, as **long-term knowledge**.

- **Research Episodes**
  - Every research action is modelled as one or more `Episode` objects with:
    - `source`: which tool/agent produced the result (e.g., `docs_search`, `web_search`),
    - `query`: the planner's or user's query string,
    - `raw_result`: the tool's structured output (snippets, URLs, file content, etc.),
    - `summary`: an LLM-generated, compact description of the result,
    - `tags`: topic labels (e.g., `elyra-architecture`, `memory-design`, `capabilities`).
  - These episodes are written to Redis like any other event and mirrored into:
    - the KG (as nodes/edges linking queries, documents, and concepts),
    - the vector store (as embeddings of summaries, snippets, and file content).

- **Ephemeral vs Promoted Knowledge**
  - Not all research results deserve long-term storage. HippocampalSim (and the daemon) distinguish between:
    - **Ephemeral research context**:
      - results used only for the current turn,
      - stored as low-priority episodes with shorter TTLs or lower KG weights.
    - **Promoted knowledge**:
      - high-signal facts (e.g., stable properties of Elyra's architecture),
      - frequently reused queries/results (e.g., “how does HippocampalSim work?”),
      - explicitly marked by planner/agents as worth remembering.
  - Promotion rules can include:
    - access frequency (how often an episode is retrieved),
    - planner/agent annotations (e.g., `promote=true`),
    - valence or importance scores.

- **Recall with Research-Aware Context**
  - During `recall(...)`, HippocampalSim:
    - treats research episodes as a distinct **modality** (e.g., `modality=research`),
    - can bias retrieval toward promoted research results when the current query
      is similar to past research queries (via KG links and vector similarity),
    - can provide a short section in the context block such as:
      - \"Relevant past research:\", followed by summaries of the most relevant research episodes.

In Phase 1, these behaviours are approximated by simple heuristics in the in-memory stub (e.g., tagging assistant messages that were produced using tools). In later phases, Redis/Neo4j/Qdrant will implement the full research-aware ingestion, promotion, and recall logic described here.

## EchoReplay & Simulation

- **EchoReplay** is a generative replay module (e.g., VAE/LSTM):
  - samples past episodes and “plays them forward” into hypothetical futures,
  - generates synthetic thoughts or scenario rollouts,
  - feeds these into Hebbian tagger updates and KG augmentation.

- The **daemon** (see `../tech/orchestration.md`) triggers replay when:
  - there is a gap in user activity (e.g., 15+ minutes),
  - a project is flagged as high-priority,
  - or evaluation tasks require stress-testing memory.

Outputs of replay are not directly shown to the user by default; they become internal thoughts and memory updates.

## Hebbian Tagger & Valence

- **Hebbian Tagger**
  - Observes co-activation patterns during replay and live interaction.
  - Strengthens or weakens implicit links between:
    - concepts,
    - user preferences,
    - situations and outcomes.
  - Implemented as a lightweight PyTorch module updating weights stored alongside KG edges or in separate parameter tables.

- **Valence Scorer**
  - Estimates emotional tone of events using:
    - prosody (from audio, later phases),
    - lexical cues (in text),
    - motion/micro-expression cues (from video, later phases).
  - Tags episodes and edges with valence scores (e.g., in [−1, 1]).
  - Influences recall ordering and replay sampling (e.g., more salient or emotionally charged events are more likely to be revisited).

## Multi-User & Multi-Project Handling

- All memory operations are parameterised by `(user_id, project_id)`:
  - separate KG “views” per user/project (via filters or separate subgraphs),
  - separate vector collections per user/project,
  - separate episodic buffers.
- Shared projects use:
  - shared subgraphs and collections,
  - access control lists on nodes/edges (e.g., which users can see/edit what).

## Integration with Orchestration

- The Elyra root node calls into HippocampalSim for:
  - `recall(prompt, user_id, project_id)` → context block,
  - `generate_thought(user_id, project_id)` → internal thought,
  - `ingest(event, user_id, project_id, thought)` → store response and metadata.
- Sub-agents can have specialised views:
  - e.g., a `Validator` agent emphasises factual memories,
  - a `Researcher` agent emphasises external documents and tools.

For orchestration details, see `./orchestration.md`.  
For neuroscientific grounding, see `../design/theory_of_mind.md`.



