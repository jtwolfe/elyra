import os

os.environ.setdefault("ELYRA_LLM_BACKEND", "mock")

from fastapi.testclient import TestClient  # noqa: E402
from elyra_backend.core.app import app  # noqa: E402


def test_chat_websocket_includes_knot_and_deltas() -> None:
    client = TestClient(app)

    with client.websocket_connect("/chat/test-user/test-project") as websocket:
        websocket.send_json({"content": "hello"})
        data = websocket.receive_json()

        assert data.get("type") == "assistant_message"
        content = data.get("content")
        thought = data.get("thought")
        trace = data.get("trace")

        assert isinstance(content, str)
        assert content.strip()
        assert content != "You said: hello"

        assert isinstance(thought, str)
        assert thought.strip()

        assert isinstance(trace, dict)
        knot = trace.get("knot")
        deltas = trace.get("deltas")

        assert isinstance(knot, dict)
        assert isinstance(knot.get("id"), str)
        assert isinstance(knot.get("primary_episode_id"), str)
        assert isinstance(knot.get("summary"), str)

        assert isinstance(deltas, list)
        assert len(deltas) >= 2, "Expected at least user + assistant deltas"


