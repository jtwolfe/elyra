from typing import List, TypedDict

from langchain_core.messages import BaseMessage


class ChatState(TypedDict):
    """
    Shared per-session state for a single user/project.

    This is intentionally minimal for the Phase 1 MVP. Additional fields
    (scratchpads, tool traces, etc.) can be added later without breaking
    the overall architecture.
    """

    messages: List[BaseMessage]
    user_id: str
    project_id: str
    # Internal thought string produced by HippocampalSim for this turn.
    # This is surfaced to the UI but is not sent back to the LLM as-is.
    thought: str


