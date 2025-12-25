---
title: Elyra API Reference (Placeholder)
audience: Engineers and integrators
status: Planned (no public API yet)
last_updated: 2025-12-03
related_docs:
  - ../design/architecture.md
  - ../tech/orchestration.md
---
> **Legacy (superseded)**: This document is preserved for reference only. The canonical Braid v2 docs live in `docs/v2/`.



### Elyra API Reference (Planned)

This file is a placeholder for a future HTTP/WebSocket API reference once Elyra’s implementation exists.

Planned high-level surface:

- **HTTP/REST**
  - `POST /api/chat` – One-shot chat endpoint (non-streaming).
  - `GET /api/memory/{user_id}/{project_id}` – Query key episodic/semantic memories.
  - `POST /api/tools/{tool_name}` – Invoke tools directly (for power users / integration tests).

- **WebSocket**
  - `WS /chat/{user_id}/{project_id}` – Primary streaming chat endpoint, emitting:
    - assistant messages,
    - internal thoughts,
    - memory lookups,
    - tool call traces.

Once the backend is implemented, replace these bullets with concrete request/response schemas and examples.


