import os

os.environ.setdefault("ELYRA_LLM_BACKEND", "mock")
os.environ.setdefault("ELYRA_ENABLE_FORKING", "0")

from elyra.runtime.braid_engine import BraidEngine  # noqa: E402


def test_semantic_bead_contains_trust_snapshot() -> None:
    e = BraidEngine("trust:test")
    e.handle_user_message("Hello. Please summarize our state.")

    rows = e.store.get_recent_bead_versions(bead_type=None, limit=50)
    semantic = [r for r in rows if (r.get("data") or {}).get("kind") == "semantic_turn_summary"]
    assert semantic, "Expected at least one semantic_turn_summary bead"

    trust = (semantic[-1].get("data") or {}).get("trust") or {}
    assert 0.0 <= float(trust.get("score") or 0.0) <= 1.0
    assert trust.get("state") in {"probation", "promoted", "demoted"}


