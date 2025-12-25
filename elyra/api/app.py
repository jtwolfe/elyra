from __future__ import annotations

from typing import Dict

from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect

from elyra.runtime.braid_engine import BraidEngine


app = FastAPI(title="Elyra (Braid v2 skeleton)")


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "arch": "braid-v2-skeleton"}


@app.websocket("/chat/{user_id}/{project_id}")
async def chat_ws(websocket: WebSocket, user_id: str, project_id: str) -> None:
    await websocket.accept()
    braid_id = f"{user_id}:{project_id}"
    engine = BraidEngine(braid_id=braid_id)

    try:
        while True:
            msg = await websocket.receive_json()
            content = (msg or {}).get("content", "")
            if not isinstance(content, str) or not content.strip():
                continue

            turn = engine.handle_user_message(content.strip())
            await websocket.send_json(
                {
                    "type": "assistant_message",
                    "content": turn.response_text,
                    "thought": turn.thought_narrative,
                    "trace": turn.trace,
                }
            )
    except WebSocketDisconnect:
        return


