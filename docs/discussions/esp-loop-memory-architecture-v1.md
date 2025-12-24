---
title: ESP Loop Memory Architecture Document (Imported)
audience: Maintainers and contributors
status: Imported reference (external)
source:
  author: "Grok 4 (xAI), based on collaborative ideation with user"
  date: 2025-12-11
  kind: "external discussion document"
last_updated: 2025-12-24
related_docs:
  - ../tech/memory-architecture.md
  - ../tech/tools-and-bootstrapping.md
  - ../tech/orchestration.md
  - ../design/architecture.md
---

# ESP Loop Memory Architecture Document

## Version History
- **Version**: 1.0
- **Date**: December 11, 2025
- **Author**: Grok 4 (xAI), based on collaborative ideation with user
- **Revision Notes**: Initial draft synthesizing concepts from discussions on graph-based memory, multi-agent systems, episodic-semantic-procedural (ESP) integration, reconciliation processes, background metacognition, dynamic tool creation, and runtime environments (e.g., Podman-based containerization).

## 1. Introduction

### 1.1 Purpose
This document outlines the architecture for **ESP Loop Memory**, a novel memory management system designed for embodied AI agents. ESP Loop Memory draws inspiration from human cognitive models, integrating **Episodic** (event-specific), **Semantic** (conceptual knowledge), and **Procedural** (step-by-step execution) memory types into a unified, loop-based framework. The system aims to enhance AI decision-making by providing context-aware, timestamped memory that supports proactive reconciliation, multi-agent collaboration, background thinking, and dynamic tool generation.

The architecture addresses challenges in existing systems, such as "stickiness" (e.g., slow queries or context overload in graph-based memory) and delegation failures in multi-agent setups. It enables AI systems to maintain temporal awareness ("embodiment"), automate context building, and scale via containerized runtimes.

### 1.2 Scope
- **In Scope**: Core memory components, agent hierarchies, data flows, reconciliation mechanisms, integration with container runtimes (e.g., Podman), dynamic tool creation, and background processes.
- **Out of Scope**: Specific implementation code (e.g., in Python or Quen 3), hardware requirements, security audits, or deployment pipelines. These can be addressed in follow-on documents.

### 1.3 Assumptions and Constraints
- **Assumptions**:
  - The system runs on a server with containerization support (e.g., Podman Desktop with AI Lab extensions).
  - Agents are powered by LLMs (e.g., Quen 3 or similar), capable of generating prompts, code, and YAML configurations.
  - Memory storage uses a graph database (e.g., Neo4j) for baseline compatibility, with extensions for vector embeddings.
  - Users interact via chat interfaces, with messages timestamped for embodiment.
- **Constraints**:
  - Resource limits: Background processes must be throttled to avoid excessive compute (e.g., <5% idle load).
  - Safety: All dynamic code/tools run in sandboxed environments to prevent escapes or crashes.
  - Scalability: Designed for single-user prototypes; multi-user extensions require sharding.

### 1.4 Key Terminology
- **ESP Loop**: A cyclic process where episodic, semantic, and procedural memories are reconciled and looped back to agents.
- **Embodiment**: Temporal grounding via timestamps on all data elements.
- **Reconciliation**: Automated merging of memory types into context chunks.
- **Metacognition**: Higher-level thinking about thinking, including planning and background "dreaming."
- **Ingress/Egress Agents**: Entry/exit points for user interactions.
- **Podman Swarm**: A network of containers for running agents and tools dynamically.

## 2. System Overview

### 2.1 High-Level Architecture
ESP Loop Memory operates as a layered system:
1. **Memory Layer**: Stores and retrieves ESP data in a hybrid graph-vector store.
2. **Agent Layer**: Hierarchical agents (top-level, metacognitive, recall, reasoning) that interact with memory.
3. **Runtime Layer**: Containerized environment (Podman-based) for executing agents, tools, and background tasks.
4. **Interaction Layer**: Ingress/egress flows for user queries and responses.

The "loop" refers to continuous feedback: new inputs trigger reconciliation, which updates memory, informing agents, which may generate new data—forming a self-improving cycle.

#### Diagram (Text-Based Representation)
```
[User Query] --> [Ingress Agent] --> [Metacognition Quorum] --> [Recall Agent] --> [ESP Memory Store]
                                                                 ↑↓ (Reconciliation Loop)
[Reasoning/Sub-Agents] <-- [Context Chunks] <-- [ESP Loop] <-- [Background Metacognition Pods]
                                                                 ↓↑ (Dynamic Tool Creation)
[Podman Swarm Runtime] --> [Tool/Worker Pods] --> [Egress Agent] --> [User Response]
```

### 2.2 Design Principles
- **Modularity**: Components (e.g., memory types) are swappable (e.g., graph for episodic, vectors for semantic).
- **Proactivity**: Background loops enable "dreaming" for anticipation and optimization.
- **Efficiency**: Pruning, caching, and asynchronous operations minimize latency.
- **Flexibility**: Agents can dynamically create tools and pods via YAML/script generation.
- **Safety and Traceability**: All actions timestamped; pods sandboxed; logs for debugging.

## 3. Core Components

### 3.1 Memory Components
ESP Loop Memory divides storage into three interconnected types, stored in a unified graph database with vector extensions (e.g., using Neo4j with vector indexes).

- **Episodic Memory**:
  - **Description**: Captures specific events, actions, or messages as timestamped sequences.
  - **Storage**: Graph nodes (e.g., "MessageNode: {id, timestamp, content, sender}"). Edges link sequences (e.g., "PRECEDED_BY").
  - **Access**: Query by time/range (e.g., "events since last user interaction").
  - **Size Management**: Prune stale entries (e.g., >30 days old, unless high-relevance via usage scores).

- **Semantic Memory**:
  - **Description**: Stores related concepts, facts, and abstractions.
  - **Storage**: Embedded vectors (e.g., using Sentence Transformers) in graph nodes (e.g., "ConceptNode: {id, embedding, labels}"). Edges for relationships (e.g., "RELATED_TO", "IS_A").
  - **Access**: Approximate nearest neighbors (ANN) searches for fast concept matching.
  - **Updates**: Automatically extracted from episodic data (e.g., NLP entity recognition).

- **Procedural Memory**:
  - **Description**: Sequences of steps for tasks, including tool calls and agent handoffs.
  - **Storage**: Script-like nodes (e.g., "ProcedureNode: {id, steps: [JSON array], inputs/outputs}"). Can include YAML for pod configs or Python snippets.
  - **Access**: Finite state machines (FSMs) or script execution for step-by-step retrieval.
  - **Dynamic Creation**: Agents generate new procedures on-the-fly, stored for reuse.

- **Unified Store**:
  - Hybrid graph-vector DB.
  - Timestamps on all nodes/edges for embodiment.
  - Reconciliation Agent: A dedicated meta-agent that merges ESP into "context chunks" (e.g., JSON payloads with episodic snippets, semantic links, procedural templates).

### 3.2 Agent Hierarchy
Agents are LLM instances (e.g., Quen 3) running in Podman pods, with prompts enforcing roles and handoffs.

- **Top-Level Agent**: Oversees planning; receives reconciled context; spins sub-agents.
- **Ingress Agent**: Handles incoming queries; performs initial metacognition (e.g., "Is this tool-related?"); timestamps and routes.
- **Egress Agent**: Summarizes outputs; strips superfluous data; ensures natural language responses.
- **Metacognition Quorum**: 3+ persistent pods voting on decisions (e.g., "Spin tool?"); enables robust planning.
- **Recall Agent**: Manages ESP queries; builds context chunks from new messages + history.
- **Reasoning Agent**: Solves problems; calls tools/sub-agents; loops back if blocked.
- **Background Metacognition Pods**: Low-priority, persistent pods for "dreaming" (e.g., replay/mutate past data to fill gaps).

Prompt Engineering: Each agent has explicit rules (e.g., "If tool needed, call X with JSON plan; await result before proceeding").

### 3.3 Runtime Environment
- **Podman Swarm**: Network of containers orchestrated via Podman Desktop/AI Lab.
  - **Ephemeral Pods**: For one-off tools (e.g., web scraper); auto-destroy after execution.
  - **Persistent Pods**: For sub-agents/metacognition; share volumes for memory access.
  - **Shared Resources**: Volumes for ESP store; networks for inter-pod communication.
- **Dynamic Tool Creation**:
  - Agents generate YAML (for pods) or scripts (e.g., Python for scraping).
  - Wrapper Tool: `run_pod(yaml_config)` – AI requests via prompt; system executes sandboxed.
  - Registry: Procedural memory stores reusable templates (e.g., "SocialScraper: {url_input, summary_output}").

### 3.4 Reconciliation Mechanism
- **Trigger**: New message or background tick (e.g., every 5 min if idle).
- **Process**:
  1. Recall Agent scans input + recent history.
  2. Pulls relevant episodic (time-based), semantic (vector similarity), procedural (pattern match).
  3. Merges into chunk: e.g., {"episodic": [snippets], "semantic": [links], "procedural": [steps]}.
  4. Overlays on target agent (e.g., via prompt injection).
- **Optimization**: Async pre-loading; pruning (e.g., relevance scores >0.5); caching common chunks.

## 4. Data Flows

### 4.1 User Query Flow
1. User sends message → Ingress timestamps → Metacognition classifies (e.g., "needs research?").
2. Recall builds ESP chunk → Routes to Reasoning (with loop if tools needed).
3. Reasoning/Sub-Agents execute (in pods) → Outputs to Egress.
4. Egress summarizes → Response to user.

### 4.2 Background Loop Flow
1. Idle trigger → Background pods replay episodic data.
2. Mutate/simulate (e.g., "What if query X?") → Generate new semantic/procedural entries.
3. Reconcile updates → Store for future use.

### 4.3 Tool Creation Flow
1. Reasoning detects gap (e.g., "Need Facebook scraper").
2. Metacognition approves → Generates YAML/script.
3. Stores in procedural → Spins ephemeral pod → Executes → Results back to loop.

## 5. Integration Points
- **With Existing Graph Memory**: Migrate to ESP by adding vector layers; use as episodic backbone.
- **With Multi-Agent Systems**: Enforce handoffs via procedural steps; fix "stickiness" with proactive chunks.
- **With Runtimes**: Podman API wrappers for agent calls; alternatives (e.g., WASM) as fallbacks for speed.
- **External Tools**: Integrate via procedural (e.g., web_search as a pod).

## 6. Implementation Considerations
- **Tech Stack**: Podman AI Lab, Neo4j (graph), FAISS (vectors), Quen 3 (agents), Python (wrappers).
- **Performance**: Target <500ms reconciliation; monitor with logs.
- **Testing**: Unit (e.g., chunk building); Integration (e.g., full query flow); Hypotheticals (e.g., Facebook scrape).
- **Scalability**: Shard memory by user; cluster Podman for multi-instance.
- **Cost**: Throttle background (e.g., event-based); use efficient ANN.

## 7. Benefits and Challenges
### 7.1 Benefits
- **Improved Context**: Reduces delegation failures; enables embodied, proactive AI.
- **Flexibility**: Dynamic tools/pods adapt to needs.
- **Efficiency**: Loops optimize over time via "dreaming."
- **Human-Like**: ESP mimics cognition for intuitive behavior.

### 7.2 Challenges and Mitigations
- **Complexity**: Hierarchical agents may loop endlessly → Limit depth (e.g., 3 iterations).
- **Resource Use**: Background churning → Throttle/thresholds.
- **Debugging**: Pod failures → Comprehensive logging; quorum voting for robustness.
- **Safety**: Dynamic code → Strict sandboxing; user veto on creations.

## 8. Future Enhancements
- Multi-user support with sharded memory.
- Integration with WASM for ultra-fast ephemeral tasks.
- Advanced "dreaming" using reinforcement learning.
- Visualization tools for ESP graph inspection.

This architecture provides a robust foundation for ESP Loop Memory, blending cognitive inspiration with practical AI engineering. Feedback welcome for iterations!


