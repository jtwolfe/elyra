---
title: Simple Implementation of ESP Loop Memory + Cognitive Engine (Imported)
audience: Maintainers and contributors
status: Imported reference (external)
source:
  author: "Conceptualized in collaboration with Grok 4 (xAI)"
  date: 2025-12-23
  kind: "external implementation concept document"
last_updated: 2025-12-24
related_docs:
  - ./esp-loop-memory-architecture-v1.md
  - ../tech/memory-architecture.md
  - ../tech/orchestration.md
---

# Architecture Document: Simple Implementation of ESP Loop Memory and Cognitive Engine Integrated with LLM

## Version: 1.0
## Date: December 23, 2025
## Authors: Conceptualized in collaboration with Grok 4 (xAI)

---

## 1. Overview

This document describes the architecture of a simple, prototype-level implementation of a cognitive tool/module designed to integrate with a Large Language Model (LLM). The system features an **ESP Loop Memory** (Episodic, Semantic, Procedural memory components) and a **Cognitive Engine** that operates as an ephemeral agent engine for running micro-tasks. The implementation is budget-friendly, runnable on a standard laptop or server with access to an Ollama instance (e.g., running a quantized 20B-parameter model like GPT-OSS 20B). It emphasizes biomimetic principles where feasible, with automatic updates, pruning, and sensor fusion for pseudo-real-time operation.

The goal is to create a self-sustaining, adaptive system that enhances the LLM's capabilities without requiring high-end hardware. This serves as a proof-of-concept to demonstrate memory retention, cognitive processing, and basic autonomy, paving the way for scaling to advanced hardware like NVIDIA DGX Spark.

Key principles:
- **Biomimetic Simplicity**: Mimic brain-like structures (e.g., episodic for experiences, semantic for facts, procedural for skills) with lightweight components.
- **Ephemeral Agents**: Micro-tasks are short-lived processes that spawn, execute, and dissolve without persistent state bloat.
- **LLM Integration**: The LLM acts as the "language brain" or reasoning core, with external modules handling memory and cognition to avoid token burn on internal thinking.
- **Resource Constraints**: No big GPUs needed; relies on CPU/GPU-accelerated Ollama for inference.

---

## 2. High-Level Architecture

The system is structured as a looped Python application wrapping an Ollama LLM instance. It consists of three main layers:

1. **Sensor/Input Layer**: Handles live data ingestion (e.g., camera, audio, text streams).
2. **Memory Layer (ESP Loop)**: A vector database for storing and retrieving linked memory components, with auto-updates and pruning.
3. **Cognitive Engine Layer**: A lightweight orchestrator that breaks tasks into ephemeral micro-agents, queries memory, invokes the LLM, and applies reinforcement-like feedback.

The LLM (via Ollama) is invoked sparingly as a "black box" reasoner, with prompts crafted to suppress unnecessary thinking and focus on outputs.

### Diagram (Text-Based Representation)

```
[Sensor Inputs]  -->  [Embedding & Fusion]  -->  [ESP Memory Loop]
   (Camera, Mic, Text)         |                       |
                               v                       v
                     [Cognitive Engine]  <-->  [LLM (Ollama Instance)]
                               |                       ^
                               v                       |
                         [Actions/Outputs]  <--  [Pruning & Feedback]
```

- **Data Flow**: Inputs are embedded and fused, stored in memory, retrieved by the cognitive engine, processed via LLM, and fed back for updates/pruning.
- **Loop Cycle**: Runs every 0.1–2 seconds for pseudo-real-time feel.

---

## 3. Components in Detail

### 3.1 Sensor/Input Layer
- **Purpose**: Fuse multimodal inputs (e.g., video frames, audio chunks, text/data streams) into a unified representation for memory storage and cognitive processing.
- **Implementation**:
  - Use OpenCV for camera access (e.g., grab frames at 30 FPS, downsample to 224x224).
  - Use sounddevice or PyAudio for audio chunks (e.g., 1-second buffers).
  - Text inputs via stdin or API (e.g., user queries).
  - **Fusion**: A simple lightweight embedder (e.g., sentence-transformers 'all-MiniLM-L6-v2') converts inputs to vectors. For multimodal, concatenate embeddings (e.g., CLIP for images + Whisper for audio transcripts).
- **Constraints**: Runs on CPU; processes in batches to avoid latency (>1s per cycle unacceptable).
- **Output**: Timestamped embedding vectors with metadata (type: episodic/semantic/procedural).

### 3.2 ESP Loop Memory
- **Purpose**: Store and link Episodic (events/experiences), Semantic (facts/concepts), and Procedural (skills/processes) memories. Auto-update without direct LLM involvement; form a "loop" via cross-references.
- **Implementation**:
  - **Backend**: ChromaDB or LanceDB (local vector database; installs via pip, runs on disk/memory).
  - **Structure**:
    - **Episodic**: Timestamped vectors of events (e.g., {"id": uuid, "embedding": vec, "timestamp": now, "content": "Saw red mug on left", "links": [semantic_id, procedural_id]}).
    - **Semantic**: Fact-based embeddings (e.g., {"id": uuid, "embedding": vec, "content": "Red mugs are fragile", "links": [episodic_ids]}).
    - **Procedural**: Graph-like skills (e.g., JSON: {"id": uuid, "steps": ["step1", "step2"], "embedding": vec, "links": [...]}).
  - **Linking**: Embeddings include cross-references; similarity search pulls linked items.
  - **Auto-Updates**: Triggered by new inputs (e.g., if similarity > threshold, update existing; else insert). No LLM—use rule-based (e.g., if-then) or lightweight ML (e.g., clustering).
  - **Pruning**: Background job (e.g., every 10 minutes or when size > threshold):
    - Use HDBSCAN for clustering old items.
    - Compress clusters to summaries (one Ollama call: "Summarize: [cluster]").
    - Delete low-relevance (e.g., unreferenced > 2 days) based on access logs.
- **Querying**: Similarity search (e.g., top-5 relevant vectors) via cosine distance.
- **Size**: Starts small (10k vectors); prunes to prevent bloat.

### 3.3 Cognitive Engine
- **Purpose**: Act as an ephemeral agent engine—break goals into micro-tasks, query memory, decide actions, and feedback loop without persistent agents.
- **Implementation**:
  - **Core Loop**: Python while-loop (e.g., every 0.1s):
    ```python
    while True:
        inputs = get_sensors()
        embeds = fuse_and_embed(inputs)
        memories = esp_memory.retrieve(embeds, top_k=5)
        prompt = build_prompt(memories, current_task)
        llm_output = ollama.generate(prompt, max_tokens=32)  # Short, focused
        action = parse_output(llm_output)
        execute_action(action)
        feedback = compute_reward(action)  # Simple: success=1, fail=0
        esp_memory.update(embeds, feedback)
        prune_if_needed()
        time.sleep(0.1)
    ```
  - **Ephemeral Micro-Agents**: Micro-tasks as disposable functions (e.g., "plan_step", "weigh_risk") spawned via if-then or finite-state machine. No long-lived threads—execute and discard.
  - **Biomimetic Elements**: Simple "spiking" via thresholds (e.g., only process if input change > delta). Reinforcement via basic rewards (e.g., track success rates, strengthen links).
  - **Metacognition**: Optional lightweight check (e.g., "Do I need this memory?" via another small prompt).
- **Complexity**: 200–500 lines of Python; modular for easy extension.

### 3.4 LLM Integration (Ollama)
- **Purpose**: Provide reasoning and language processing without internal "thinking" loops.
- **Implementation**:
  - **Model**: Quantized 20B (e.g., GPT-OSS 20B Q4_0 for speed/memory).
  - **Prompt Engineering**: System prompt suppresses auto-thinking: "You are a raw substrate. Output only actions/results. No reasoning unless <think>."
  - **Invocation**: Via Ollama API; single-pass generation (max 32–64 tokens) to minimize burn.
  - **Role**: Acts as the "spokesperson"—receives memory-infused prompts, outputs decisions/actions.
- **Limitations**: No direct KV-cache access; context resets per call (mitigated by external memory injections).

---

## 4. Key Processes

### 4.1 Initialization
- Load Ollama model.
- Initialize ChromaDB collection.
- Start sensor loop.

### 4.2 Runtime Cycle
- Ingest → Embed → Retrieve → Prompt → LLM → Act → Update/Prune.

### 4.3 Pruning & Feedback
- Homeostasis: Monitor load; prune via age/relevance.
- RL-Lite: Adjust weights (e.g., boost successful memory links).

---

## 5. Dependencies & Setup
- **Python Packages**: chromadb, opencv-python, sounddevice, numpy, sentence-transformers, ollama (API client).
- **Hardware**: Laptop/server with Ollama on RTX 5090 (or equivalent); webcam/mic for sensors.
- **Setup Script**:
  ```bash
  pip install chromadb opencv-python sounddevice numpy sentence-transformers
  ollama run gpt-oss-20b:q4_0  # Example model
  python esp_demo.py
  ```

---

## 6. Limitations & Scalability
- **Limitations**: Pseudo-real-time (0.1–2s latency); no true continuous inference; memory external (potential loss on crash).
- **Scalability Path**: Migrate to vLLM/llama.cpp for KV manipulation; upgrade to DGX Spark for full fusion and internal looping.
- **Testing**: Demo via video: Show memory recall/pruning in 30s.

This architecture provides a functional, testable prototype. For evolution to advanced implementations, refer to companion documents on DGX Spark transitions.


