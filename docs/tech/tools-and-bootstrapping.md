---
title: Tools and Bootstrapping – From Basics to Self-Generated Tools
audience: Engineers and contributors
status: Phase 1 MVP - Baseline tools implemented, bootstrapping planned
last_updated: 2025-12-10
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

**Current Implementation (Phase 1)** - All tools registered in `elyra_backend/tools/registry.py`:

- **Web / HTTP** ✅ **IMPLEMENTED**
  - `web_search(query, top_k=5)` – Uses LangChain's `DuckDuckGoSearchRun` for internet searches. Returns structured results with titles, URLs, and snippets. Includes error handling for rate limiting, timeouts, and empty results.
  - `browse_page(url, max_chars=4000)` – Fetches web page content via HTTP, trims to max_chars, returns structured result with content and metadata.

- **Code / Evaluation** ✅ **PARTIALLY IMPLEMENTED**
  - `code_exec(snippet, language="python")` – Sandboxed Python execution using temporary files and subprocess isolation. Returns stdout/stderr with execution results. **Note**: Full sandboxing (resource limits, network restrictions) is planned for future phases.

- **Project / Files** ✅ **IMPLEMENTED**
  - `read_project_file(path)` – Reads local project files (relative to workspace root). Returns file content with error handling for missing files and permission errors.

- **Documentation Search** ✅ **IMPLEMENTED**
  - `docs_search(query, top_k=5)` – Semantic search over `docs/` directory:
    - **Primary**: ChromaDB-based vector search using sentence-transformers embeddings (if ChromaDB available)
    - **Fallback**: String-based search if ChromaDB unavailable (Python 3.14 compatibility issues)
    - Returns results with `path`, `content`, `chunk_index`, `score`, `source_reference`
    - Auto-indexes on first use

- **Utilities** ✅ **IMPLEMENTED**
  - `get_time()` – Returns current UTC time in ISO 8601 format.
  - `echo(text)` – Echo utility for testing.
  - `summarize_text(text, max_chars=200)` – Heuristic text summarization.
  - `echo_with_time(text)` – Echo with timestamp prefix.

**Tool Registry**: Central `ToolRegistry` class manages registration, discovery (`list_tools()`), and execution (`execute(name, **args)`). All tools are strongly typed with clear error semantics.

## Tool Registry

**Current Implementation** (`elyra_backend/tools/registry.py`):

Elyra uses a central `ToolRegistry` class that:

- ✅ **holds all manually defined tools** - Built-in tools registered in `_register_builtins()`
- ✅ **exposes registration APIs** - `register(tool: Tool)` method for adding new tools
- ✅ **integrates with LangChain** - Uses `DuckDuckGoSearchRun` from `langchain_community`
- 🔄 **LLM-generated tools** - Planned for future phases (bootstrapping loop)

Core responsibilities:

- ✅ **Discovery**: `list_tools()` returns `Dict[str, str]` mapping tool names to descriptions
- ✅ **Execution**: `execute(name: str, **kwargs)` runs tools and returns structured results:
  - Handles both sync and async tools
  - Returns tool-specific structured outputs (Dict[str, Any])
  - Errors are caught and returned in result dicts with `error` field
- 🔄 **Audit**: Tool usage tracked in `ChatState["tools_used"]` and `ChatState["tool_results"]` for observability

**Tool Structure**:
```python
@dataclass
class Tool:
    name: str
    description: str  # Used by planner to understand capabilities
    func: Callable[..., Any]  # Tool implementation
```

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

## Tool Implementation Details

### Web Search Tool (`web_search`)

**Implementation**: Uses LangChain's `DuckDuckGoSearchRun` wrapped in `asyncio.to_thread()` for async compatibility.

**Features**:
- Returns structured results with `title`, `url`, `snippet` fields
- Parses DuckDuckGo's string output into structured format
- Error handling for:
  - Rate limiting (429 status codes)
  - Network timeouts (`httpx.HTTPError`)
  - Invalid queries (empty query strings)
  - Empty results

**Usage**: Called by `researcher_sub` for external information queries.

### Documentation Search Tool (`docs_search`)

**Implementation**: Dual-mode search with automatic fallback.

**Primary Mode (ChromaDB)**:
- Uses `DocsVectorStore` class (`elyra_backend/tools/docs_vector_store.py`)
- Indexes `docs/*.md` files on first use:
  - Chunks markdown by paragraphs (`\n\n` separator)
  - Embeds chunks using `sentence-transformers/all-MiniLM-L6-v2`
  - Stores in ChromaDB with metadata (path, chunk_index)
- Semantic search returns:
  - `path`: File path
  - `content`: Full chunk content
  - `chunk_index`: Chunk index within file
  - `score`: Similarity distance (lower = more similar)
  - `source_reference`: `{path}#chunk-{index}` for citations

**Fallback Mode (String Search)**:
- Automatically used if ChromaDB unavailable (Python 3.14 compatibility issues)
- Simple substring search across all `.md` files
- Returns same structure as ChromaDB mode for API consistency
- **Current Status**: ChromaDB 0.3.23 has Pydantic 2.x compatibility issues; fallback is active

**Error Handling**:
- Indexing failures: Returns error message, retries on next call
- DB connection errors: Falls back to string search
- Empty results: Returns error message with query

### Multi-Shot Researcher Agent (`researcher_sub`)

**Implementation**: Iterative tool executor in `elyra_backend/core/app.py`.

**Iteration Strategy**:
- **Iteration 0**: `docs_search` (for project-specific questions)
- **Iteration 1**: `web_search` (for external information)
- **Iteration 2+**: `browse_page` (if URLs found) or retries with alternatives

**Retry Logic**:
- Checks `has_sufficient_results()` against `RESEARCHER_MIN_RESULTS_THRESHOLD` (default: 1)
- Retries if results insufficient (`should_retry()`)
- Maximum iterations: `RESEARCHER_MAX_ITERATIONS` (default: 3)

**Tool Chaining**:
- Can chain `web_search` → `browse_page` (extracts URLs from search results)
- Can chain `docs_search` → `read_project_file` (for deeper file inspection)

**Summary Generation**:
- `build_multi_iteration_summary()` aggregates all tool results
- Includes source attribution (`source_reference` for docs, URLs for web)
- Formats as structured text for LLM consumption

**Logging**:
- Iteration counts logged: `"Researcher: Starting iteration {n}/{max}"`
- Tool execution logged: `"Researcher: Executing tool {name} with args {args}"`
- Success/failure logged with error details
- Final summary logged: `"Researcher: Successfully gathered information from {tool_count} tools"`

## Error Message Reference

**Comprehensive error messages** are logged throughout the system for debugging and observability. All messages follow a consistent format: `"{Agent}: {Message}"`.

### Planner Sub-Agent (`planner_sub`)
- `"Planner: Failed to parse LLM response - {error}"` - JSON parsing failure in `<plan>` tags
- `"Planner: LLM response missing required <plan> tags"` - Fallback JSON extraction attempted
- `"Planner: Fallback JSON extraction succeeded: route={route}, tools={tools}"` - Success using regex fallback
- `"Planner: Fallback JSON extraction also failed: {error}"` - Both parsing methods failed
- `"Planner: Invalid delegate_to value: {value}, defaulting to 'end'"` - Invalid routing decision
- `"Planner: Tool specification invalid: {tool_spec}"` - Malformed tool in plan
- `"Planner: Context adequacy score indicates sparse context ({score}), recommending research tools"` - Low adequacy triggers research

### Researcher Sub-Agent (`researcher_sub`)
- `"Researcher: Starting multi-shot research for query: {query}"` - Research initiated
- `"Researcher: Starting iteration {n}/{max_iterations}"` - Iteration start
- `"Researcher: Executing tool {name} with args {args}"` - Tool execution start
- `"Researcher: Tool {name} execution failed: {error}"` - Tool execution error
- `"Researcher: Results insufficient, retrying with alternative approach"` - Retry triggered
- `"Researcher: Sufficient results gathered after {n} iterations"` - Success condition met
- `"Researcher: Maximum iterations reached ({max_iterations}), stopping research"` - Iteration limit hit
- `"Researcher: No more tools to try, stopping"` - No tools available for next iteration
- `"Researcher: Successfully gathered information from {tool_count} tools across {iteration_count} iterations"` - Final success summary

### Root Agent (`elyra_root`)
- `"Root: Executing {count} planned tools"` - Tool execution start
- `"Root: Successfully executed tool {name}"` - Tool success
- `"Root: Tool {name} execution failed: {error}"` - Tool execution error
- `"Root: Successfully executed {count} tools, ingesting to memory"` - Memory ingestion start
- `"Root: Memory ingestion failed for tool result: {error}"` - Memory ingestion error
- `"Root: LLM response parsing failed, using raw response"` - Thought extraction failure

### Validator Sub-Agent (`validator_sub`)
- `"Validator: Placeholder validator - no validation performed (Phase 1)"` - Phase 1 placeholder
- `"Validator: Future implementation will check factual consistency"` - Future work note

### Tool-Level Errors (returned in `tool_results`)
- **`web_search`**: `"Web search encountered rate limiting"`, `"Web search failed: network error - {error}"`
- **`docs_search`**: `"Documentation search returned no results for query: {query}"`, `"Documentation indexing in progress, please retry"`
- **`browse_page`**: `"Failed to fetch URL: {error}"`, `"Page content too large, truncated"`
- **`read_project_file`**: `"File not found: {path}"`, `"Permission denied: {path}"`
- **`code_exec`**: `"Code execution failed: {error}"`, `"Execution timeout"`



