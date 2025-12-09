from typing import Any, Dict, List, TypedDict

from langchain_core.messages import BaseMessage


class ChatState(TypedDict):
    """
    Shared per-session state for a single user/project.

    This now captures the core pieces needed for routing, memory, planning,
    and basic observability in the Phase 1–2 roadmap.
    """

    messages: List[BaseMessage]
    user_id: str
    project_id: str

    # Internal thought string for this turn, as surfaced to the UI. For now
    # this is typically derived from an LLM <think>...</think> block in the
    # final answer step.
    thought: str

    # Names of tools invoked during this turn. This is primarily used for
    # debugging and for building dev-facing traces of internal behaviour.
    tools_used: List[str]

    # Free-form internal notes or routing annotations. Nodes can append to
    # this to aid with later inspection in debug panels.
    scratchpad: str

    # Planner-driven routing decision: "researcher", "validator", "end", or
    # None if no explicit route has been chosen yet.
    route: str | None

    # Planner's requested tools for this turn.
    planned_tools: List[Dict[str, Any]]

    # Actual tool execution results for this turn.
    tool_results: List[Dict[str, Any]]

