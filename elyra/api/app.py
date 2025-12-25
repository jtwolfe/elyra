from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocketDisconnect

from elyra.runtime.braid_engine import BraidEngine
from elyra.runtime.background import BackgroundWorkerGroup
from elyra.runtime.settings import get_v2_settings


app = FastAPI(title="Elyra (Braid v2 skeleton)")

# Dev-friendly CORS (UI runs on :5173, API on :8000).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Best-effort engine registry so inspector endpoints can see in-memory state
# for braids that have an active websocket session.
_ENGINE_LOCK = asyncio.Lock()
_ENGINES: dict[str, BraidEngine] = {}


async def _get_or_create_engine(braid_id: str) -> BraidEngine:
    async with _ENGINE_LOCK:
        eng = _ENGINES.get(braid_id)
        if eng is None:
            eng = BraidEngine(braid_id=braid_id)
            _ENGINES[braid_id] = eng
        return eng


def _dump(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")  # type: ignore[attr-defined]
        except Exception:
            return obj.model_dump()  # type: ignore[attr-defined]
    return obj


async def _reset_all_state(confirm: str) -> dict[str, Any]:
    settings = get_v2_settings()
    if not settings.ENABLE_DANGEROUS_ADMIN:
        raise HTTPException(status_code=404, detail="Not found")
    if confirm != "reset":
        raise HTTPException(status_code=400, detail="Confirmation required: type 'reset'")

    # Clear in-process engines first (best-effort close).
    async with _ENGINE_LOCK:
        for eng in list(_ENGINES.values()):
            try:
                eng.store.close()
            except Exception:
                pass
        _ENGINES.clear()

    neo4j_deleted = False
    qdrant_deleted: list[str] = []

    # Neo4j wipe (dev-only): delete all nodes in the current DB.
    if settings.PERSISTENCE_BACKEND.lower().strip() == "neo4j":
        try:
            from neo4j import GraphDatabase  # type: ignore

            driver = GraphDatabase.driver(
                settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            with driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
            try:
                driver.close()
            except Exception:
                pass
            neo4j_deleted = True
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Neo4j reset failed: {exc}")

    # Qdrant wipe: delete all collections (dev-only).
    try:
        import httpx

        base = str(settings.QDRANT_URL).rstrip("/")
        with httpx.Client(base_url=base, timeout=10.0) as client:
            r = client.get("/collections")
            r.raise_for_status()
            data = r.json() or {}
            cols = data.get("result", {}).get("collections") or []
            for c in cols:
                name = (c or {}).get("name") if isinstance(c, dict) else None
                if not isinstance(name, str) or not name:
                    continue
                try:
                    d = client.delete(f"/collections/{name}")
                    d.raise_for_status()
                    qdrant_deleted.append(name)
                except Exception:
                    continue
    except Exception:
        # Qdrant may be down; keep best-effort.
        pass

    return {"ok": True, "neo4j_deleted": neo4j_deleted, "qdrant_deleted": qdrant_deleted}


async def _snapshot_for(braid_id: str, *, deltas_limit: int, knots_limit: int) -> dict[str, Any]:
    eng = await _get_or_create_engine(braid_id)
    store = eng.store
    settings = get_v2_settings()

    deltas = []
    knots = []
    episodes = []
    beads = []

    try:
        deltas = [_dump(d) for d in store.get_recent_deltas(int(deltas_limit))]
    except Exception:
        deltas = []
    try:
        knots = [_dump(k) for k in store.get_recent_knots(int(knots_limit))]
    except Exception:
        knots = []
    try:
        episodes = [_dump(e) for e in store.list_episodes(limit=50)]  # type: ignore[attr-defined]
    except Exception:
        episodes = []
    try:
        beads = list(store.get_recent_bead_versions(bead_type=None, limit=50))  # type: ignore[attr-defined]
    except Exception:
        beads = []

    active_episode = None
    try:
        active_episode = _dump(store.get_active_episode())  # type: ignore[attr-defined]
    except Exception:
        active_episode = None

    return {
        "braid_id": braid_id,
        "settings": {
            "persistence_backend": settings.PERSISTENCE_BACKEND,
            "enable_forking": settings.ENABLE_FORKING,
            "enable_background_workers": settings.ENABLE_BACKGROUND_WORKERS,
        },
        "active_episode": active_episode,
        "episodes": episodes,
        "knots": knots,
        "deltas": deltas,
        "beads": beads,
    }

@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "arch": "braid-v2-skeleton"}


@app.get("/admin/reset/status")
async def reset_status() -> dict[str, Any]:
    settings = get_v2_settings()
    if not settings.ENABLE_DANGEROUS_ADMIN:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True, "enabled": True}


@app.post("/admin/reset/all")
async def reset_all(payload: dict[str, Any]) -> dict[str, Any]:
    confirm = str((payload or {}).get("confirm") or "")
    return await _reset_all_state(confirm)


@app.get("/inspect/{user_id}/{project_id}/snapshot")
async def inspect_snapshot(
    user_id: str,
    project_id: str,
    deltas_limit: int = 200,
    knots_limit: int = 50,
) -> dict[str, Any]:
    braid_id = f"{user_id}:{project_id}"
    return await _snapshot_for(braid_id, deltas_limit=deltas_limit, knots_limit=knots_limit)


@app.get("/inspect/{user_id}/{project_id}/deltas")
async def inspect_deltas(user_id: str, project_id: str, limit: int = 200) -> dict[str, Any]:
    braid_id = f"{user_id}:{project_id}"
    snap = await _snapshot_for(braid_id, deltas_limit=limit, knots_limit=0)
    return {"braid_id": braid_id, "deltas": snap.get("deltas") or []}


@app.get("/inspect/{user_id}/{project_id}/knots")
async def inspect_knots(user_id: str, project_id: str, limit: int = 50) -> dict[str, Any]:
    braid_id = f"{user_id}:{project_id}"
    snap = await _snapshot_for(braid_id, deltas_limit=0, knots_limit=limit)
    return {"braid_id": braid_id, "knots": snap.get("knots") or []}


@app.get("/inspect/{user_id}/{project_id}/episodes")
async def inspect_episodes(user_id: str, project_id: str) -> dict[str, Any]:
    braid_id = f"{user_id}:{project_id}"
    snap = await _snapshot_for(braid_id, deltas_limit=0, knots_limit=0)
    return {
        "braid_id": braid_id,
        "active_episode": snap.get("active_episode"),
        "episodes": snap.get("episodes") or [],
    }


@app.get("/inspect/{user_id}/{project_id}/beads")
async def inspect_beads(user_id: str, project_id: str) -> dict[str, Any]:
    braid_id = f"{user_id}:{project_id}"
    snap = await _snapshot_for(braid_id, deltas_limit=0, knots_limit=0)
    return {"braid_id": braid_id, "beads": snap.get("beads") or []}


@app.websocket("/chat/{user_id}/{project_id}")
async def chat_ws(websocket: WebSocket, user_id: str, project_id: str) -> None:
    await websocket.accept()
    braid_id = f"{user_id}:{project_id}"
    engine = await _get_or_create_engine(braid_id)
    workers: BackgroundWorkerGroup | None = None
    settings = get_v2_settings()
    if settings.ENABLE_BACKGROUND_WORKERS:
        workers = BackgroundWorkerGroup(
            engine=engine,
            dream_interval_s=settings.DREAM_INTERVAL_SECONDS,
            metacog_interval_s=settings.METACOG_INTERVAL_SECONDS,
        )
        await workers.start()

    try:
        while True:
            msg = await websocket.receive_json()
            content = (msg or {}).get("content", "")
            if not isinstance(content, str) or not content.strip():
                continue

            try:
                turn = engine.handle_user_message(content.strip())
                await websocket.send_json(
                    {
                        "type": "assistant_message",
                        "content": turn.response_text,
                        "thought": turn.thought_narrative,
                        "trace": turn.trace,
                    }
                )
            except Exception as exc:
                # Keep the WS alive on transient LLM/tool failures.
                await websocket.send_json(
                    {
                        "type": "error",
                        "content": f"Backend error: {exc}",
                        "trace": {"error": {"message": str(exc)}},
                    }
                )
    except WebSocketDisconnect:
        return
    finally:
        if workers is not None:
            try:
                await workers.stop()
            except Exception:
                pass


