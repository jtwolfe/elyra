import asyncio
from typing import Any, Dict, List

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from elyra_backend.core.app import app, app_graph
from elyra_backend.core.state import ChatState


async def _fake_chat(self: Any, messages: List[Dict[str, Any]]) -> str:  # type: ignore[override]
    """
    Minimal fake OllamaClient.chat implementation for tests.

    It allows graph and websocket tests to run without a real Ollama server.
    """
    # Basic assertion that messages are passed through.
    assert isinstance(messages, list)
    assert messages, "Expected at least one message"
    return "hello from fake ollama"


def test_chat_graph_returns_thought(monkeypatch: Any) -> None:
    """
    Ensure that a simple graph invocation returns both an AIMessage and a thought.
    """
    # Patch OllamaClient.chat so no real HTTP call is made.
    monkeypatch.setattr(
        "elyra_backend.llm.ollama_client.OllamaClient.chat",
        _fake_chat,
        raising=True,
    )

    async def run() -> None:
        state: ChatState = {
            "messages": [HumanMessage(content="hello")],
            "user_id": "u1",
            "project_id": "p1",
            # Initial thought value is not used by the node but included for type completeness.
            "thought": "",
            "tools_used": [],
            "scratchpad": "",
            "route": None,
            "planned_tools": [],
            "tool_results": [],
        }
        result = await app_graph.ainvoke(state)
        messages = result.get("messages") or []
        assert messages, "Expected at least one AI message in result"
        assert isinstance(messages[-1], AIMessage)

        thought = result.get("thought")
        assert isinstance(thought, str)
        assert thought.strip(), "Thought should be a non-empty string"

    asyncio.run(run())


def test_chat_websocket_includes_thought(monkeypatch: Any) -> None:
    """
    Ensure that the WebSocket /chat endpoint returns assistant messages with thoughts.
    """
    # Patch OllamaClient.chat so no real HTTP call is made.
    monkeypatch.setattr(
        "elyra_backend.llm.ollama_client.OllamaClient.chat",
        _fake_chat,
        raising=True,
    )

    client = TestClient(app)

    with client.websocket_connect("/chat/test-user/test-project") as websocket:
        websocket.send_json({"content": "hello"})
        data = websocket.receive_json()

        assert data.get("type") == "assistant_message"
        content = data.get("content")
        thought = data.get("thought")
        trace = data.get("trace")

        assert isinstance(content, str)
        assert content.strip(), "Assistant content should be non-empty"

        assert isinstance(thought, str)
        assert thought.strip(), "Thought should be a non-empty string"

        # Trace information should be present for the debug panel.
        assert isinstance(trace, dict)
        assert "tools_used" in trace
        assert "scratchpad" in trace


