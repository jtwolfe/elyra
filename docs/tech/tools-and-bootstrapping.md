---
title: Tools and Bootstrapping – From Basics to Self-Generated Tools
audience: Engineers and contributors
status: Planned design (no implementation yet)
last_updated: 2025-12-03
related_docs:
  - ./llm-stack.md
  - ./orchestration.md
---

## Overview

Tools are how Elyra interacts with the outside world (web, code, APIs, files, sensors).  
This document covers:

- the **baseline tool set**,
- the **Tool Registry** abstraction,
- and the **bootstrapping loop** for LLM-generated tools.

## Baseline Tool Set

Initial tools will likely include:

- **Web / HTTP**
  - `browse_page(url)` – fetch and summarise a web page.
  - `web_search(query)` – call a search API and return top results.

- **Code / Evaluation**
  - `code_exec(snippet, language)` – run code in a sandbox.
  - `unit_tests(run_id)` – execute a pre-defined test suite.

- **Project / Files**
  - `read_file(path)` – read project files (with access controls).
  - `write_file(path, content)` – propose file changes (HITL approval recommended).

- **Utilities**
  - `get_time()` – retrieve current time.
  - `log_event(event)` – log notable internal events for later review.

Exact tool names are flexible; the key is to maintain **clear, strongly typed signatures** and **good error semantics**.

## Tool Registry

Elyra uses a central `ToolRegistry` that:

- holds all manually defined tools,
- exposes registration APIs for new tools (including LLM-generated ones),
- integrates with LangChain or native function-calling APIs.

Core responsibilities:

- **Discovery**: return a list of available tools with:
  - name, description, argument schema.
- **Execution**: run the selected tool and return a structured result:
  - success flag,
  - outputs,
  - error messages / stack traces if any.
- **Audit**: record when and how tools were used for later analysis.

## Tool Generation (Bootstrapping)

The bootstrapping loop lets Elyra propose and refine new tools:

1. **Need Detection**
   - The LLM identifies gaps, e.g.:
     - frequent calls to a sequence of primitive tools,
     - repeated user tasks that could be automated.

2. **Specification Draft**
   - Elyra generates a natural-language and schema-level spec:
     - purpose,
     - input/output types,
     - constraints and side effects.

3. **Code Synthesis**
   - A “tool-creator” prompt asks the LLM to write:
     - the tool function,
     - tests or check cases,
     - documentation.

4. **Validation**
   - Run the proposed tool in a sandbox:
     - execute tests,
     - check type hints and linting,
     - evaluate behaviour on a small set of examples.

5. **Review & Registration**
   - Human (or strict policy) approves the tool.
   - ToolRegistry registers the new tool with a stable name and schema.

6. **Monitoring & Retiring**
   - Usage and failure rates are tracked.
   - Poorly performing tools are:
     - improved via another refinement loop, or
     - deprecated and removed.

## VeRL-Style Refinement

“VeRL-style” here refers to low-data RL or bandit-style loops that:

- treat tools or tool parameters as policies,
- reward success on tasks (e.g., tests passed, user satisfaction proxies),
- adjust tool selection or implementation over time.

Possible integration:

- maintain a small pool of tool variants,
- collect outcome metrics,
- periodically promote/demote variants based on performance.

## Safety and Governance

- **Permissioning**
  - Some tools require explicit user consent (e.g., external network, file writes).
  - Tools can be scoped per user/project.

- **Sandboxing**
  - Code execution and file access are sandboxed:
    - restricted file system roots,
    - resource limits,
    - no direct network access from untrusted code.

- **Review Process**
  - New tools (especially LLM-generated) pass through:
    - static checks (linters, type checkers),
    - dynamic tests,
    - human sign-off for high-impact capabilities.

For details on how the LLM is prompted to call tools, see `./llm-stack.md`.  
For when and where tools run in the graph, see `./orchestration.md`.



