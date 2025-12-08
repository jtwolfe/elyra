---
title: Elyra Quickstart (Conceptual)
audience: Engineers and advanced users
status: Conceptual design + Phase 1 notes
last_updated: 2025-12-03
related_docs:
  - ../design/architecture.md
  - ../tech/llm-stack.md
---

### Important note

This file has **two layers**:

- A **Phase 1: Actual quickstart** for the minimal text‑only MVP that exists in this repo.
- A **Conceptual quickstart** that sketches the fully‑featured system from the design docs.

The conceptual example is **illustrative pseudocode** and not meant to match the current code one‑to‑one.

### Phase 1: Actual quickstart (implemented MVP)

For concrete, up‑to‑date commands, see `RUNNING_LOCALLY.md`. In short:

1. **Start Ollama (LLM backend)**  
   Run `ollama serve` and ensure the model in `elyra_backend/config.py` (by default `mistral:7b-instruct-v0.3-q6_K`) is available.
2. **Run the backend API**  
   Start Uvicorn with the FastAPI app in `elyra_backend/core/app.py`, which exposes:
   - `GET /health` for basic status,
   - `WS /chat/{user_id}/{project_id}` for the chat UI.
3. **Run the React/Tailwind Web UI**  
   From `ui/`, run `npm install` and `npm run dev`, then open the printed URL in your browser.

The Web UI connects to the backend WebSocket and renders:

- chat messages between user and Elyra,
- an “Internal thought” side panel showing stubbed thoughts from `HippocampalSim`.

### Conceptual quickstart

At a high level, a minimal text‑only Elyra deployment will include:

- A **FastAPI** app that exposes a WebSocket endpoint for chat.
- A **LangGraph** workflow that wraps the Elyra “root” agent.
- A **HippocampalSim** memory core that handles recall, replay, tagging, and ingestion.
- An **LLM client** (e.g., Mistral‑7B via Ollama) for generating responses.
- A **Tool registry** (e.g., LangChain tools) for browsing pages, searching, and later self‑generated tools.

Below is the conceptual `quickstart.py` from the design:

```python
# quickstart.py — conceptual example of a minimal Elyra app
import uvicorn
from fastapi import FastAPI, WebSocket
from langgraph.graph import StateGraph, START, END
from hippocampal_sim import HippocampalSim
from llm.ollama import OllamaClient
from tools import ToolRegistry  # For basics + bootstrap
import asyncio
from typing import Annotated, TypedDict, List
from langchain_core.messages import add_messages, BaseMessage

app = FastAPI(title="Elyra v1")
ollama = OllamaClient(
    base_url="http://your-ollama-host:11434",
    model="mistral:7b-instruct-v0.3-q6_K",
)
hippo = HippocampalSim(ollama=ollama)  # KG + Redis + daemon
tools = ToolRegistry(hippo)  # Load basics (e.g., browse_page)


class ChatState(TypedDict):
    """Per-session state for a single user/project."""

    messages: Annotated[List[BaseMessage], add_messages]
    user_id: str
    project_id: str  # For multi-user isolation


async def elyra_node(state: ChatState):
    # 1. Recall relevant memories (tiers + valence)
    context = await hippo.recall(
        state["messages"][-1].content,
        state["user_id"],
        state["project_id"],
    )
    # 2. Add internal thought (proactive if gap)
    thought = await hippo.generate_thought(
        state["user_id"],
        state["project_id"],
    )
    # 3. Tool calls if needed (bootstrap check)
    if needs_tools(thought):  # TODO: implement prompt logic
        tool_result = await tools.execute(state["messages"][-1].content)
        context += tool_result
    # 4. Call LLM
    response = await ollama.chat(
        [
            {"role": "system", "content": hippo.system_prompt + thought},
            *state["messages"],
            {"role": "system", "content": context},
        ]
    )
    # 5. Store everything
    await hippo.ingest(
        response,
        state["user_id"],
        state["project_id"],
        thought,
    )
    return {"messages": [response]}


workflow = StateGraph(ChatState)
workflow.add_node("elyra", elyra_node)
workflow.add_edge(START, "elyra")
workflow.add_edge("elyra", END)
app_graph = workflow.compile()


@app.websocket("/chat/{user_id}/{project_id}")
async def chat_ws(websocket: WebSocket, user_id: str, project_id: str):
    """WebSocket endpoint for the Web UI."""

    await websocket.accept()
    while True:
        msg = await websocket.receive_json()
        async for chunk in app_graph.astream(
            {
                "messages": [msg],
                "user_id": user_id,
                "project_id": project_id,
            }
        ):
            await websocket.send_json(chunk)  # Stream thoughts/memory/actions


if __name__ == "__main__":
    # NOTE: In a real app, use FastAPI startup events or asyncio.run().
    asyncio.create_task(hippo.daemon_loop())
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Intended run sequence

Once the implementation exists, the basic run flow will look like:

```bash
docker compose up -d neo4j redis
python quickstart.py
# then open http://localhost:3000 for the Web UI
```

The Web UI connects to `/chat/{user_id}/{project_id}` over WebSockets, and renders:

- chat messages,
- internal “thought” bubbles,
- memory snapshots (KG panels),
- and action/tool logs.


