from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MockLLMClient:
    """Offline-safe LLM stub for unit tests and local dev without network.

    - chat_json(): returns deterministic structured output
    - chat(): returns deterministic assistant response
    """

    def chat_json(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = str(m.get("content") or "")
                break

        tool_calls: list[dict[str, Any]] = []
        # Very small heuristic: if user asks to "search" or "docs", propose docs_search.
        lower = user_msg.lower()
        if "docs" in lower or "search" in lower or "documentation" in lower:
            tool_calls.append({"name": "docs_search", "args": {"query": user_msg, "max_hits": 5}})

        fork = {
            "should_fork": False,
            "confidence": 0.0,
            "reason": "",
            "candidate_episode_labels": {"topics": [], "intents": [], "modalities": []},
        }
        # Simple drift trigger for tests: explicit "switch topics" proposes a fork.
        if "switch topics" in lower:
            fork = {
                "should_fork": True,
                "confidence": 0.9,
                "reason": "Explicit topic switch requested.",
                "candidate_episode_labels": {"topics": ["topic_switch"], "intents": [], "modalities": ["text"]},
            }

        # Detect microagent prompt vs knot think-pass prompt by checking system instructions.
        system_text = ""
        for m in reversed(messages):
            if m.get("role") == "system":
                system_text = str(m.get("content") or "")
                break

        if "MICROAGENT TOOL-SELECTION" in system_text.upper():
            return {
                "tool_calls": tool_calls,
                "notes": "I selected tools based on the goal.",
            }

        microagent_request = {
            "should_spawn": bool(tool_calls),
            "goal": user_msg if tool_calls else "",
            "requested_tools": [c["name"] for c in tool_calls],
            "notes": "Spawn a microagent for tool use." if tool_calls else "",
        }

        return {
            "thought_summary": "I reviewed the recent context and prepared a response.",
            "microagent_request": microagent_request,
            "fork": fork,
            "assumptions": [],
            "hypotheses": [],
        }

    def chat(self, messages: list[dict[str, Any]]) -> str:
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = str(m.get("content") or "")
                break
        # Keep stable and non-empty.
        return f"(mock) I received your message and will respond helpfully.\n\nYou said:\n{user_msg}".strip()


