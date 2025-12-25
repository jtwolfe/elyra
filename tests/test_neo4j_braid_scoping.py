import os

import pytest


def _neo4j_available() -> bool:
    # Only run when explicitly enabled (dev environment) to avoid CI flakiness.
    return os.environ.get("ELYRA_RUN_NEO4J_TESTS", "0").strip() in {"1", "true", "yes"}


@pytest.mark.skipif(not _neo4j_available(), reason="Neo4j integration tests disabled (set ELYRA_RUN_NEO4J_TESTS=1).")
def test_neo4j_get_recent_bead_versions_is_braid_scoped() -> None:
    os.environ.setdefault("ELYRA_PERSISTENCE_BACKEND", "neo4j")
    os.environ.setdefault("ELYRA_NEO4J_URI", "bolt://localhost:7687")
    os.environ.setdefault("ELYRA_NEO4J_USER", "neo4j")
    os.environ.setdefault("ELYRA_NEO4J_PASSWORD", "password")
    os.environ.setdefault("ELYRA_LLM_BACKEND", "mock")

    from elyra.runtime.braid_engine import BraidEngine
    from lmm.schema.bead import BeadType

    a = BraidEngine("scope:test:a")
    b = BraidEngine("scope:test:b")

    a.handle_user_message("A-only message")
    b.handle_user_message("B-only message")

    beads_a = a.store.get_recent_bead_versions(bead_type=BeadType.memory_bead, limit=50)
    beads_b = b.store.get_recent_bead_versions(bead_type=BeadType.memory_bead, limit=50)

    assert all(r.get("braid_id") == "scope:test:a" for r in beads_a), "Expected only braid A beads"
    assert all(r.get("braid_id") == "scope:test:b" for r in beads_b), "Expected only braid B beads"


