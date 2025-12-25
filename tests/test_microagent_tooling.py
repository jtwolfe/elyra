import os

os.environ.setdefault("ELYRA_LLM_BACKEND", "mock")

from elyra.runtime.braid_engine import BraidEngine
from lmm.schema.delta import DeltaKind


def test_tools_execute_via_microagent_with_audit_refs() -> None:
    e = BraidEngine("ma:test")
    e.handle_user_message("Search the docs for Braid v2 and summarize.")

    deltas = e.store.get_recent_deltas(200)
    tool_calls = [d for d in deltas if d.kind == DeltaKind.tool_call]
    tool_results = [d for d in deltas if d.kind == DeltaKind.tool_result]
    microagent = [d for d in deltas if d.kind == DeltaKind.microagent]

    assert microagent, "Expected a microagent delta"
    assert tool_calls and tool_results, "Expected tool_call and tool_result deltas"

    # Tool deltas must carry refs tying them back to the microagent bead + tool bead.
    for d in tool_calls + tool_results:
        payload = d.payload or {}
        assert payload.get("microagent_bead_ref"), "Expected microagent_bead_ref on tool delta"
        assert payload.get("tool_bead_ref"), "Expected tool_bead_ref on tool delta"
        assert (d.provenance.episode_id or "").startswith("episode:tools:"), "Expected tool episode provenance"


