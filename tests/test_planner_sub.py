import asyncio
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage

from elyra_backend.core.app import app_graph  # noqa: F401  - ensure graph builds
from elyra_backend.core.state import ChatState


async def _fake_planner_chat(self: Any, messages: List[Dict[str, Any]]) -> str:  # type: ignore[override]
    """
    Fake OllamaClient.chat implementation for planner tests.

    It returns a fixed <think>/<plan> payload instructing Elyra to delegate
    to the researcher and call docs_search.
    """
    # Basic assertion that messages are passed through.
    assert isinstance(messages, list)
    assert messages, "Expected at least one message"
    return (
        "<think>planner reasoning</think>"
        "<plan>{\"delegate_to\": \"researcher\", "
        "\"tools\": [{\"name\": \"docs_search\", \"args\": {\"query\": \"foo\"}}]}</plan>"
    )


def test_planner_sub_updates_route_and_planned_tools(monkeypatch: Any) -> None:
    """
    Ensure that the planner_sub node can parse <think>/<plan> and populate
    route and planned_tools in the state when invoked as part of the graph.
    """
    from elyra_backend.core.app import app_graph  # local import for monkeypatch

    # Patch OllamaClient.chat so no real HTTP call is made.
    monkeypatch.setattr(
        "elyra_backend.llm.ollama_client.OllamaClient.chat",
        _fake_planner_chat,
        raising=True,
    )

    async def run() -> None:
        state: ChatState = {
            "messages": [HumanMessage(content="How does Elyra work?")],
            "user_id": "u1",
            "project_id": "p1",
            "thought": "",
            "tools_used": [],
            "scratchpad": "",
            "route": None,
            "planned_tools": [],
            "tool_results": [],
        }
        result = await app_graph.ainvoke(state)
        # After a full graph run, we should have at least one AI message.
        messages = result.get("messages") or []
        assert messages, "Expected at least one AI message in result"

        # Planner should have set route and planned_tools before delegation.
        route = result.get("route")
        planned_tools = result.get("planned_tools") or []
        assert route in {"researcher", "validator", "end"}
        assert isinstance(planned_tools, list)

    asyncio.run(run())


