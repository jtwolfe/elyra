from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional
import subprocess
import sys
import tempfile

import httpx


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
        self.register(
            Tool(
                name="docs_search",
                description=(
                    "Search the local Elyra documentation for a query string and "
                    "return up to `top_k` matching snippets."
                ),
                func=self._tool_docs_search,
            )
        )
        self.register(
            Tool(
                name="web_search",
                description=(
                    "Use DuckDuckGo's instant answer API to perform a small web "
                    "search and return top matches."
                ),
                func=self._tool_web_search,
            )
        )
        self.register(
            Tool(
                name="browse_page",
                description=(
                    "Fetch and return a trimmed text representation of a web page."
                ),
                func=self._tool_browse_page,
            )
        )
        self.register(
            Tool(
                name="code_exec",
                description=(
                    "Execute a short Python snippet in a temporary sandboxed "
                    "directory and return stdout/stderr/exit code."
                ),
                func=self._tool_code_exec,
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

    @staticmethod
    def _tool_docs_search(query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Perform a very small, heuristic search over the local docs/ tree.

        This is deliberately simple for the MVP: it scans text files under
        ``docs/`` for the query string (case-insensitive), extracts a short
        snippet around each match, and returns the top_k results ranked by
        a naive score (count of query occurrences).
        """
        query_clean = (query or "").strip()
        if not query_clean:
            return {"query": query, "results": []}

        docs_root = Path("docs")
        if not docs_root.exists():
            return {"query": query, "results": []}

        needle = query_clean.lower()
        hits: List[Dict[str, Any]] = []

        for path in docs_root.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                # Skip unreadable files.
                continue

            lowered = text.lower()
            if needle not in lowered:
                continue

            score = lowered.count(needle)
            idx = lowered.find(needle)
            # Take a small window around the first occurrence.
            start = max(0, idx - 120)
            end = min(len(text), idx + len(needle) + 120)
            snippet = text[start:end].strip()

            hits.append(
                {
                    "path": str(path),
                    "score": score,
                    "snippet": snippet,
                }
            )

        # Sort by descending score and then path for determinism.
        hits.sort(key=lambda h: (-h["score"], h["path"]))
        return {
            "query": query,
            "results": hits[: max(0, top_k)],
        }

    @staticmethod
    async def _tool_web_search(query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Perform a small web search using DuckDuckGo's instant answer API.

        This is intended for lightweight research; it does not require an API
        key but should be treated as best-effort only and not relied on for
        production-grade search.
        """
        query_clean = (query or "").strip()
        if not query_clean:
            return {"query": query, "results": []}

        params = {
            "q": query_clean,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("https://api.duckduckgo.com/", params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return {"query": query, "results": [], "error": "web_search_failed"}

        results: List[Dict[str, Any]] = []

        # DuckDuckGo Instant Answer returns 'RelatedTopics' which may contain
        # either direct results or nested 'Topics' lists.
        for item in data.get("RelatedTopics", []):
            if "Text" in item and "FirstURL" in item:
                results.append(
                    {
                        "title": item.get("Text", ""),
                        "url": item.get("FirstURL", ""),
                    }
                )
            elif "Topics" in item:
                for sub in item.get("Topics", []):
                    if "Text" in sub and "FirstURL" in sub:
                        results.append(
                            {
                                "title": sub.get("Text", ""),
                                "url": sub.get("FirstURL", ""),
                            }
                        )

        return {
            "query": query,
            "results": results[: max(0, top_k)],
        }

    @staticmethod
    async def _tool_browse_page(url: str, max_chars: int = 4000) -> Dict[str, Any]:
        """
        Fetch a web page and return a trimmed text representation.

        This is deliberately simple and does not execute JavaScript; it is meant
        for quick content inspection rather than full browser emulation.
        """
        url_clean = (url or "").strip()
        if not url_clean:
            return {"url": url, "error": "empty url", "content": ""}

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url_clean)
        except Exception:
            return {"url": url_clean, "error": "fetch_failed", "content": ""}

        text = resp.text or ""
        # Extremely naive HTML tag stripping to keep dependencies light.
        # For more robust behaviour, integrate an HTML parser (e.g. BeautifulSoup).
        import re

        stripped = re.sub(r"<[^>]+>", " ", text)
        stripped = re.sub(r"\s+", " ", stripped).strip()
        if len(stripped) > max_chars:
            content = stripped[: max_chars - 3] + "..."
        else:
            content = stripped

        return {
            "url": url_clean,
            "status_code": resp.status_code,
            "content_type": resp.headers.get("content-type", ""),
            "error": None,
            "content": content,
        }

    @staticmethod
    def _tool_code_exec(
        snippet: str, language: str = "python", timeout_seconds: float = 3.0
    ) -> Dict[str, Any]:
        """
        Execute a short code snippet in a very lightweight sandbox.

        Currently only supports Python. The code runs in a temporary directory
        with a small timeout. This is *not* a security-hardened sandbox and
        should not be exposed directly to untrusted users in production.
        """
        lang = (language or "").lower()
        if lang != "python":
            return {
                "language": language,
                "error": "unsupported language; only 'python' is supported",
                "stdout": "",
                "stderr": "",
                "returncode": None,
                "timeout": False,
            }

        code = (snippet or "").strip()
        if not code:
            return {
                "language": language,
                "error": "empty snippet",
                "stdout": "",
                "stderr": "",
                "returncode": None,
                "timeout": False,
            }

        with tempfile.TemporaryDirectory(prefix="elyra_code_exec_") as tmpdir:
            try:
                proc = subprocess.run(
                    [sys.executable, "-c", code],
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    cwd=tmpdir,
                    env={
                        "PYTHONUNBUFFERED": "1",
                    },
                )
                return {
                    "language": "python",
                    "error": None,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "returncode": proc.returncode,
                    "timeout": False,
                }
            except subprocess.TimeoutExpired as exc:
                return {
                    "language": "python",
                    "error": "timeout",
                    "stdout": exc.stdout or "",
                    "stderr": exc.stderr or "",
                    "returncode": None,
                    "timeout": True,
                }

    @staticmethod
    def _tool_read_project_file(path: str, max_chars: int = 2000) -> Dict[str, Any]:
        """
        Read a project file from disk with simple safety checks.

        This is intended for research-style inspection of local source/docs.
        It only allows paths under the current working directory and returns
        at most `max_chars` characters of content.
        """
        raw_path = (path or "").strip()
        if not raw_path:
            return {"path": path, "error": "empty path", "content": ""}

        requested = Path(raw_path)
        try:
            resolved = requested.resolve()
            root = Path(".").resolve()
        except OSError:
            return {"path": path, "error": "invalid path", "content": ""}

        # Disallow escaping the project root.
        try:
            resolved.relative_to(root)
        except ValueError:
            return {"path": str(requested), "error": "path outside project root", "content": ""}

        if not resolved.exists() or not resolved.is_file():
            return {"path": str(requested), "error": "file not found", "content": ""}

        try:
            text = resolved.read_text(encoding="utf-8")
        except OSError:
            return {"path": str(requested), "error": "unable to read file", "content": ""}

        if len(text) > max_chars:
            content = text[: max_chars - 3] + "..."
        else:
            content = text

        return {"path": str(requested), "error": None, "content": content}


