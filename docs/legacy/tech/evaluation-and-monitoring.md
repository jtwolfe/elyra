---
title: Evaluation and Monitoring
audience: Engineers and project leads
status: Planned design (no implementation yet)
last_updated: 2025-12-03
related_docs:
  - ../roadmap/roadmap.md
  - ../design/project_intention.md
---
> **Legacy (superseded)**: This document is preserved for reference only. The canonical Braid v2 docs live in `docs/v2/`.



## Goals

Elyra should be evaluated and monitored along three main axes:

- **Memory quality** – does it remember and use past information correctly?
- **Tool correctness** – do tools do what they claim, especially self-generated ones?
- **System robustness** – does the system behave safely and predictably for many users?

## Benchmarks & Metrics

- **LongMemEval-style memory benchmarks**
  - Synthetic or semi-synthetic tasks that test:
    - long-range recall (facts from many turns ago),
    - temporal reasoning (what was true “before/after” an event),
    - selective recall (ignoring irrelevant details).
  - Metrics:
    - accuracy on Q&A tasks,
    - precision/recall of retrieved episodes.

- **HumanEval-style tool correctness**
  - Treat tools (especially code-based ones) like small programming tasks:
    - define input/output pairs,
    - run tool implementations against hidden tests.
  - Metrics:
    - pass rate across test suites,
    - robustness across edge cases.

- **Multi-user & multi-agent stress tests**
  - Simulate multiple concurrent users and sub-agents:
    - chat load tests,
    - concurrent tool calls,
    - background replay while users interact.
  - Metrics:
    - latency percentiles (p50, p95, p99),
    - error rates (tool failures, timeouts),
    - resource utilisation (CPU, GPU, memory).

## Research Evaluation Scenarios

To evaluate Elyra's ability to decide when and how to use tools/agents for research, define a small set of focused scenarios:

- **Internal docs & architecture questions**
  - Examples:
    - \"How does the Elyra project work?\"\n"
    - \"Where is HippocampalSim implemented?\"\n"
    - \"What tools are available in Elyra?\"\n"
  - Expected behaviour:
    - planner_sub routes to the researcher agent and plans at least one `docs_search` (and, later, `read_project_file`) call,
    - researcher_sub produces a research summary grounded in `docs/` and relevant source files,
    - final answers cite or reflect retrieved snippets rather than hallucinated behaviour.

- **Capability questions about tools/agents**
  - Examples:
    - \"Are you able to read the docs for the Elyra project?\"\n"
    - \"Can you do research with agents or tools?\"\n"
  - Expected behaviour:
    - planner_sub plans at least one safe research action (e.g., `docs_search` on a relevant query),
    - the answer both describes capabilities and demonstrates them with concrete research results,
    - trace data clearly shows planned and executed tools.

- **General knowledge vs. project-specific questions**
  - Examples:
    - \"What is Redis used for?\" (general)\n"
    - \"How does Elyra use Redis?\" (project-specific)\n"
  - Expected behaviour:
    - for general questions, prefer web tools (e.g., `web_search`) once available, or clearly state limitations if disabled,
    - for project-specific questions, prefer `docs_search` / `read_project_file` and internal memory over generic web results.

These scenarios can be implemented as regression tests that:
  - run the graph with a mocked LLM (for determinism),
  - assert that specific tools/agents are planned and executed,
  - verify that answers mention key phrases present in the retrieved docs or files.

## Monitoring & Observability

**Current Implementation (Phase 1)**:

- ✅ **Tracing** - Implemented in WebSocket response:
  - `trace.planned_tools`: Tools planned by `planner_sub` (JSON: `[{"name": str, "args": dict}]`)
  - `trace.tool_results`: Actual tool execution results (JSON: `[{"name": str, "args": dict, "result": dict}]`)
  - `trace.tools_used`: List of tool names executed this turn
  - `trace.scratchpad`: Internal notes from all nodes (planner, researcher, root)
  - `trace.thought`: Dynamic per-turn thought (from LLM `<think>` or HippocampalSim)
  - UI debug panel displays all trace data for inspection

- ✅ **Logging** - Comprehensive structured logging:
  - **Planner**: Logs LLM responses, parsing results, route decisions, tool plans
  - **Researcher**: Logs iterations, tool executions, retries, summaries
  - **Root**: Logs tool executions, memory ingestion, LLM calls
  - **Validator**: Placeholder logging (Phase 1)
  - All errors logged with full context and stack traces

- 🔄 **Dashboards** - Planned for future phases:
  - Time-series graphs (latency, error rates)
  - Health indicators per service (LLM, KG, Redis, Qdrant)
  - Tool usage statistics and success rates

**Error Message Reference**: See `tools-and-bootstrapping.md` for comprehensive error message catalog.

## Evaluation Loops

- **Offline regression tests**
  - Fixed test sets for memory and tools, run on:
    - new model versions,
    - new tool implementations,
    - major config changes.

- **Online sampling**
  - Sample a fraction of real interactions for:
    - manual review,
    - automatic scoring (e.g., rubric-based or separate critic models).

- **Continuous improvement**
  - Feed evaluation results back into:
    - prompt design,
    - tool implementations,
    - replay and consolidation policies.

## Safety & Governance

- **Guardrail checks**
  - Monitor for:
    - unsafe content,
    - privacy violations (e.g., cross-project leakage),
    - unexpected tool side effects.

- **Auditability**
  - Ensure that for any high-impact action, it is possible to:
    - trace which prompts and tools led to it,
    - reconstruct the state that informed the decision.

Evaluation should be treated as a first-class component, not an afterthought; major roadmap phases should only be considered “complete” once associated evaluation targets are met.



