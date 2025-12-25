---
title: Elyra Glossary
audience: All readers
status: In progress (will expand as docs evolve)
last_updated: 2025-12-03
related_docs:
  - ../overview/intro.md
---
> **Legacy (superseded)**: This document is preserved for reference only. The canonical Braid v2 docs live in `docs/v2/`.



### Glossary

Short definitions of recurring terms and technologies used across Elyra’s docs.

- **A2A (Agent-to-Agent)**: Communication and coordination patterns between sub-agents within Elyra’s LangGraph workflow (e.g., passing messages, merging results).

- **APScheduler**: A Python scheduling library used here to run background jobs such as gap-detection daemons and replay cycles.

- **Bi-temporal KG**: A knowledge graph that tracks both **valid time** (when a fact is true in the world) and **transaction time** (when it was written/updated), enabling “time-travel” queries and soft deletion.

- **EchoReplay**: Elyra’s planned module for replaying and simulating past experiences using generative models (e.g., VAE/LSTM) to consolidate memory and imagine futures.

- **Episodic Buffer**: Short-term store of recent events (dialogue turns, sensor frames) before they are consolidated into long-term KG and vector memory.

- **Graphiti**: A temporal knowledge-graph abstraction used to manage entities, relations, and time-stamped edges; backed by a graph database such as Neo4j.

- **Hebbian Tagger**: A component that updates connection strengths (“weights”) between memory traces based on co-activation, inspired by the Hebbian rule (“cells that fire together, wire together”).

- **HippocampalSim**: The core memory system in Elyra, acting as an analogue of the hippocampus and related structures; orchestrates episodic buffer, replay, tagging, KG, and vector store.

- **HumanEval**: A widely-used benchmark of short programming tasks; here, it stands in for “tool correctness” tests when Elyra generates or refines code-based tools.

- **KG (Knowledge Graph)**: A structured representation of entities and relationships (nodes and edges), used in Elyra for long-term, symbolic memory.

- **LangChain**: A Python framework for building LLM-powered applications with tools, retrievers, and chains; used to define and call tools (e.g., via `StructuredTool`).

- **LangGraph**: A graph-based orchestration framework used to define Elyra’s agent workflows (root agent + sub-agents, branching, and state management).

- **LongMemEval**: A family of benchmarks that evaluate an AI system’s ability to recall and use information over long histories, often with complicated temporal structure.

- **Memorious**: A research system focused on very long-term memory for AI (e.g., hierarchical KGs and retrieval), referenced as inspiration for Elyra’s memory design.

- **Mistral-7B / Llama 3.x (OSS LLMs)**: Open-source large language models used as Elyra’s “neocortex” (fast pattern completion and language). Smaller models power early phases; larger ones support tool bootstrapping and complex reasoning.

- **Ollama**: A lightweight LLM serving platform that runs models locally or on a remote host; Elyra uses an Ollama client to talk to models such as Mistral or Llama.

- **Qdrant**: A vector database used to store and search dense embeddings (e.g., of dialogue turns, documents, or sensor data) for semantic similarity retrieval.

- **Replay (Hippocampal Replay)**: The process of reactivating past experiences during rest/idle periods to consolidate memories or plan; in Elyra, implemented via EchoReplay + daemon loops.

- **Tool Bootstrapping**: The process by which Elyra uses an LLM to propose, implement, and refine new tools (e.g., LangChain tools), often guided by templates and evaluation loops.

- **ToolGen-style patterns**: A general label for research patterns where LLMs generate tool definitions or APIs from natural language descriptions or task requirements.

- **VeRL**: A reinforcement-learning-style toolkit and approach used in these docs as shorthand for low-data RL methods that refine LLM-generated tools and behaviours.

- **WebUI**: The React + Tailwind front-end that exposes Elyra to end users, showing chats, internal thoughts, memory snippets, and action logs.

This glossary is not exhaustive; as you introduce new concepts or external systems, please add concise, non-marketing definitions here.


