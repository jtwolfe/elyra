import os

# IMPORTANT: set env before app import so runtime settings pick it up.
os.environ.setdefault("ELYRA_LLM_BACKEND", "ollama")
os.environ.setdefault("ELYRA_OLLAMA_MODEL", "gpt-oss:latest")
os.environ.setdefault(
    "ELYRA_OLLAMA_BASE_URL_PRIMARY", "http://localhost:11434"
)
os.environ.setdefault(
    "ELYRA_OLLAMA_BASE_URL_FALLBACK", "http://localhost:11434"
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from elyra_backend.core.app import app  # noqa: E402


@pytest.mark.skipif(
    os.environ.get("ELYRA_LIVE_OLLAMA", "0") not in {"1", "true", "yes"},
    reason="Set ELYRA_LIVE_OLLAMA=1 to enable live Ollama integration test.",
)
def test_live_ollama_websocket_round_trip() -> None:
    client = TestClient(app)
    with client.websocket_connect("/chat/live-user/live-project") as websocket:
        websocket.send_json({"content": "Say hello in one short sentence."})
        data = websocket.receive_json()
        assert data.get("type") == "assistant_message"
        assert isinstance(data.get("content"), str)
        assert data["content"].strip()


