import os

os.environ.setdefault("ELYRA_LLM_BACKEND", "mock")
os.environ.setdefault("ELYRA_ENABLE_FORKING", "1")
os.environ.setdefault("ELYRA_FORK_CONFIRMATION_REQUIRED", "1")

from fastapi.testclient import TestClient  # noqa: E402

from elyra_backend.core.app import app  # noqa: E402


def test_fork_pending_can_promote_to_active_episode() -> None:
    client = TestClient(app)
    with client.websocket_connect("/chat/fork-user/fork-project") as websocket:
        websocket.send_json({"content": "We are working on Elyra."})
        websocket.receive_json()

        # Mock LLM triggers a fork when message contains "switch topics"
        websocket.send_json({"content": "Switch topics: tell me a cake recipe."})
        data = websocket.receive_json()

        assert data.get("type") == "assistant_message"
        trace = data.get("trace") or {}
        episode = trace.get("episode") or {}
        assert episode.get("id")
        assert episode.get("state") in {"active", "fork_pending"}, "Episode state should be present"

        # With confirmation_required=1, we should promote immediately on proposal.
        # If promotion occurs, primary_episode_id should match the active episode id.
        assert trace.get("primary_episode_id") == episode.get("id")


