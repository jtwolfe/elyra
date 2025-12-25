import os

os.environ.setdefault("ELYRA_LLM_BACKEND", "mock")

from elyra.runtime.braid_engine import BraidEngine  # noqa: E402
from lmm.schema.bead import BeadType  # noqa: E402


def test_dream_tick_writes_dream_replay_bead() -> None:
    e = BraidEngine("bg:test:dream")
    e.handle_user_message("Hello.")
    e.dream_tick()

    rows = e.store.get_recent_bead_versions(bead_type=BeadType.memory_bead, limit=200)
    dream = [r for r in rows if (r.get("data") or {}).get("kind") == "dream_replay"]
    assert dream, "Expected a dream_replay bead after dream_tick()"


def test_metacog_tick_writes_fork_params_bead() -> None:
    e = BraidEngine("bg:test:metacog")
    e.handle_user_message("Hello.")
    e.metacog_tick()

    rows = e.store.get_recent_bead_versions(bead_type=BeadType.memory_bead, limit=200)
    meta = [r for r in rows if (r.get("data") or {}).get("kind") == "metacog_fork_params"]
    assert meta, "Expected a metacog_fork_params bead after metacog_tick()"

