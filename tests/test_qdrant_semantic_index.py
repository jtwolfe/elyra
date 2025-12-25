import os

import pytest

from elyra.runtime.vector.qdrant_semantic import QdrantSemanticIndex


@pytest.mark.skipif(
    os.environ.get("ELYRA_RUN_QDRANT_TESTS", "0").strip() not in {"1", "true", "yes"},
    reason="Qdrant integration tests disabled (set ELYRA_RUN_QDRANT_TESTS=1).",
)
def test_qdrant_semantic_index_search_against_running_qdrant() -> None:
    # Use deterministic tiny embedder to avoid loading real models.
    def embed(texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            t = t or ""
            out.append([float(len(t)), float(t.count("a")), float(t.count(" "))+1.0])
        return out

    idx = QdrantSemanticIndex(
        qdrant_url=os.environ.get("ELYRA_QDRANT_URL", "http://localhost:6333"),
        braid_id="core",
        embedding_model_name="unused",
        embedder=embed,
    )
    idx.upsert_semantic_bead(
        bead_version_id="v1",
        user_text="Jamie likes techno",
        assistant_text="Noted.",
        payload={"kind": "semantic_turn_summary"},
    )
    hits = idx.search(query="techno", top_k=5)
    assert hits
    assert hits[0].payload.get("kind") == "semantic_turn_summary"


