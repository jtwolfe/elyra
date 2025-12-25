---
title: LLM Stack – Models, Serving, and Prompting
audience: Engineers and ML practitioners
status: Planned design (no implementation yet)
last_updated: 2025-12-03
related_docs:
  - ../design/architecture.md
  - ./tools-and-bootstrapping.md
---
> **Legacy (superseded)**: This document is preserved for reference only. The canonical Braid v2 docs live in `docs/v2/`.



## Goals

Elyra’s LLM layer acts as the “neocortex”: fast pattern completion, language understanding, and generation.  
The design emphasises:

- **Model swapability** (Mistral, Llama, etc.),
- **Clear prompting conventions**,
- **Support for tool calls and self-generated tools**,
- **Resource awareness** (local vs. remote GPUs).

## Model Choices by Phase

- **Early phases (1–2): efficiency first**
  - Example: Mistral-7B or similar models served via **Ollama**.
  - Goals:
    - Reasonably fast responses on commodity hardware.
    - Sufficient quality for conversation, recall, and basic tools.

- **Middle phases (3–4): stronger reasoning and coding**
  - Example: Llama 3.x 8B/70B (or analogous OSS models) via:
    - Ollama on a GPU host, or
    - HuggingFace `transformers` + `vllm`/`text-generation-inference`.
  - Goals:
    - Better long-horizon reasoning.
    - More reliable tool invocation and code generation.

- **Later phases (5–6): specialised variants**
  - Fine-tuned variants or mixtures (e.g., code-focused vs. multimodal).
  - Possible split:
    - “Dialogue/Orchestration” model.
    - “Tool creation / coding” model.

Exact model names can evolve, but the interface to Elyra should remain stable.

## Serving Layer

- **Ollama Client**
  - Thin wrapper providing:
    - model selection and routing,
    - streaming and non-streaming calls,
    - basic health checks.
  - Configured via environment:
    - base URL,
    - model name or alias,
    - per-request timeouts and max tokens.

- **Direct HF / vLLM (optional)**
  - For teams not using Ollama:
    - a separate adapter can expose the same interface but target HF or vLLM.
  - Constraint: the orchestration layer must not depend on the serving backend.

## Prompting & Context Assembly

Each LLM call in Elyra follows a structured pattern:

1. **System prompt**
   - Encodes Elyra’s role, safety policies, and core behaviour.
   - Contains a compressed description of:
     - memory semantics (episodic vs. semantic),
     - tool usage rules,
     - multi-user expectations.

2. **Memory-derived context**
   - Output of `hippocampal_sim.recall(...)`:
     - key episodes,
     - relevant KG snippets,
     - vector-retrieved summaries.
   - Inserted as one or more `system` or `assistant` messages with clear delimiters (e.g., “BEGIN MEMORY CONTEXT”).

3. **Conversation history**
   - Selected subset of recent messages (not full history).
   - Trimmed for length and relevance.

4. **Latest user input**
   - The most recent user message, optionally annotated with:
     - project metadata,
     - UI hints (e.g., which panel is active).

The orchestrator assembles this into a message list for the LLM client and then post-processes the result for tools and memory ingestion.

## Tool Use and Function-Call Style

Elyra uses tool-aware prompting patterns so the LLM can:

- decide *when* to call a tool,
- emit well-formed tool arguments,
- and incorporate tool results into final answers.

Implementation options:

- **LangChain-style tools**
  - Describe tools with JSON schemas (`StructuredTool`).
  - Let the LLM emit JSON for tool calls in a dedicated channel.

- **Native function-calling APIs**
  - If the serving backend supports function calling, map Elyra tools to those definitions.

Regardless of mechanism, Elyra’s prompts should:

- clearly list available tools and their signatures,
- instruct the model to avoid hallucinating tools that do not exist,
- include guidelines for retrying or backing off after tool errors.

## Safety & Guardrails

- **System-level instructions**
  - No exfiltration of secrets.
  - Respect user/project boundaries.
  - Defer to human when unsure about high-impact actions.

- **Content filtering**
  - Optional wrapper that rejects or sanitises unsafe generations based on:
    - regex rules,
    - heuristic filters,
    - or external moderation services.

- **Tool guardrails**
  - Some tools are restricted to:
    - specific projects,
    - specific users or roles,
    - or sandboxed environments (e.g., code execution).

## Observability

- Log per-call metadata:
  - model name/version,
  - latency and token usage,
  - whether tools were used,
  - basic error codes.
- Use traces (e.g., LangSmith-style) to:
  - inspect prompts,
  - evaluate quality over time,
  - debug failures.

For tool design, see `./tools-and-bootstrapping.md`.  
For orchestration graphs, see `./orchestration.md`.



