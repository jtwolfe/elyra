from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional


ToolFunc = Callable[..., Any]


@dataclass
class Tool:
    name: str
    description: str
    func: ToolFunc


class ToolRegistry:
    """
    Very small tool registry for the Phase 1 MVP.

    It supports a couple of built-in tools and can be extended later
    with LangChain `StructuredTool` instances or similar abstractions.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        self.register(
            Tool(
                name="get_time",
                description="Return the current UTC time in ISO 8601 format.",
                func=self._tool_get_time,
            )
        )
        self.register(
            Tool(
                name="echo",
                description="Echo back the provided text.",
                func=self._tool_echo,
            )
        )
        self.register(
            Tool(
                name="summarize_text",
                description=(
                    "Return a very short heuristic summary of the provided text."
                ),
                func=self._tool_summarize_text,
            )
        )
        self.register(
            Tool(
                name="echo_with_time",
                description=(
                    "Echo back the provided text alongside the current UTC time."
                ),
                func=self._tool_echo_with_time,
            )
        )

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def list_tools(self) -> Dict[str, str]:
        """Return a mapping of tool name to description."""
        return {name: t.description for name, t in self._tools.items()}

    async def execute(self, name: str, **kwargs: Any) -> Any:
        """Execute the named tool with the given keyword arguments."""
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")

        result = tool.func(**kwargs)
        if isinstance(result, Awaitable):
            return await result
        return result

    # Built-in tool implementations -------------------------------------------------

    @staticmethod
    def _tool_get_time() -> str:
        now = datetime.now(timezone.utc)
        return now.isoformat()

    @staticmethod
    def _tool_echo(text: Optional[str] = None) -> str:
        return text or ""

    @staticmethod
    def _tool_summarize_text(text: Optional[str] = None, max_chars: int = 200) -> str:
        """
        Return a trivial heuristic summary of the provided text.

        This is intentionally simple for the MVP: it trims leading/trailing
        whitespace and returns at most ``max_chars`` characters.
        """
        if not text:
            return ""
        cleaned = text.strip()
        if len(cleaned) <= max_chars:
            return cleaned
        return cleaned[: max_chars - 3] + "..."

    @staticmethod
    def _tool_echo_with_time(text: Optional[str] = None) -> str:
        """Echo back the provided text prefixed with the current UTC time."""
        now = datetime.now(timezone.utc).isoformat()
        body = text or ""
        return f"[{now}] {body}"


