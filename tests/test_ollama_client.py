import asyncio
from typing import Any, Dict, List

import httpx

from elyra_backend.llm.ollama_client import OllamaClient


class _FakeResponse:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Dict[str, Any]:
        return self._payload


async def _fake_post(self, url: str, json: Dict[str, Any]) -> _FakeResponse:  # type: ignore[override]
    # Minimal assertion that the OllamaClient passes model and messages through.
    assert "model" in json
    assert "messages" in json
    return _FakeResponse({"message": {"content": "hello from ollama"}})


def test_ollama_client_chat_uses_response_content(monkeypatch: Any) -> None:
    # Patch AsyncClient.post so no real HTTP request is made.
    monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post, raising=True)

    client = OllamaClient(base_url="http://example.com", model="test-model")

    async def run() -> None:
        messages: List[Dict[str, Any]] = [{"role": "user", "content": "hi"}]
        result = await client.chat(messages)
        assert result == "hello from ollama"

    asyncio.run(run())


