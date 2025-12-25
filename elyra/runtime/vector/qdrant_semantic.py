from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

import httpx

def _slug(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()


Embedder = Callable[[list[str]], list[list[float]]]


@dataclass
class SemanticHit:
    score: float
    payload: dict[str, Any]


class QdrantSemanticIndex:
    """Minimal per-braid semantic index in Qdrant (Phase 1 rewire).

    Stores embeddings of semantic beads so ribbon assembly can retrieve top-K relevant summaries.
    """

    def __init__(
        self,
        *,
        qdrant_url: str,
        braid_id: str,
        embedding_model_name: str,
        embedder: Optional[Embedder] = None,
    ) -> None:
        self._braid_id = braid_id
        self._collection = f"elyra_semantic_{_slug(braid_id)}"
        self._qdrant_url = qdrant_url.rstrip("/")

        if embedder is not None:
            self._embed = embedder
            self._dim = len(embedder(["dim_probe"])[0])
        else:
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._model = SentenceTransformer(embedding_model_name)
            self._dim = int(self._model.get_sentence_embedding_dimension())

            def _default_embed(texts: list[str]) -> list[list[float]]:
                return self._model.encode(texts).tolist()

            self._embed = _default_embed

        self._ensure_collection()

    @property
    def collection_name(self) -> str:
        return self._collection

    def _ensure_collection(self) -> None:
        # GET /collections
        with httpx.Client(base_url=self._qdrant_url, timeout=10.0) as client:
            r = client.get("/collections")
            r.raise_for_status()
            data = r.json() or {}
            existing = {c.get("name") for c in (data.get("result", {}).get("collections") or []) if isinstance(c, dict)}
            if self._collection in existing:
                return
            # PUT /collections/{name}
            r2 = client.put(
                f"/collections/{self._collection}",
                json={"vectors": {"size": int(self._dim), "distance": "Cosine"}},
            )
            r2.raise_for_status()

    def upsert_semantic_bead(
        self,
        *,
        bead_version_id: str,
        user_text: str,
        assistant_text: str,
        payload: dict[str, Any],
    ) -> None:
        doc = (user_text or "").strip() + "\n\n" + (assistant_text or "").strip()
        vec = self._embed([doc])[0]
        with httpx.Client(base_url=self._qdrant_url, timeout=30.0) as client:
            r = client.put(
                f"/collections/{self._collection}/points",
                params={"wait": "true"},
                json={
                    "points": [
                        {
                            "id": bead_version_id,
                            "vector": vec,
                            "payload": {
                                "braid_id": self._braid_id,
                                "user_text": user_text,
                                "assistant_text": assistant_text,
                                **(payload or {}),
                            },
                        }
                    ]
                },
            )
            r.raise_for_status()

    def search(self, *, query: str, top_k: int) -> list[SemanticHit]:
        q = (query or "").strip()
        if not q:
            return []
        vec = self._embed([q])[0]
        with httpx.Client(base_url=self._qdrant_url, timeout=30.0) as client:
            r = client.post(
                f"/collections/{self._collection}/points/search",
                json={"vector": vec, "limit": int(top_k), "with_payload": True},
            )
            r.raise_for_status()
            data = r.json() or {}
            hits = data.get("result") or []
        out: list[SemanticHit] = []
        for h in hits:
            if not isinstance(h, dict):
                continue
            out.append(SemanticHit(score=float(h.get("score") or 0.0), payload=dict(h.get("payload") or {})))
        return out


