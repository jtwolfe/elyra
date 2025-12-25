from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional
import subprocess
import sys
import tempfile

import httpx
from langchain_community.tools import DuckDuckGoSearchRun
from elyra_backend.tools.docs_vector_store import DocsVectorStore

ToolFunc = Callable[..., Any]

@dataclass
class Tool:
    name: str
    description: str
    func: ToolFunc

class ToolRegistry:
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
                description="Return a very short heuristic summary of the provided text.",
                func=self._tool_summarize_text,
            )
        )
        self.register(
            Tool(
                name="echo_with_time",
                description="Echo back the provided text alongside the current UTC time.",
                func=self._tool_echo_with_time,
            )
        )
        self.register(
            Tool(
                name="docs_search",
                description="Perform semantic search over Elyra documentation using ChromaDB.",
                func=self._tool_docs_search,
            )
        )
        self.register(
            Tool(
                name="web_search",
                description="Perform a web search using LangChain's DuckDuckGoSearchRun.",
                func=self._tool_web_search,
            )
        )
        self.register(
            Tool(
                name="browse_page",
                description="Fetch and return a trimmed text representation of a web page.",
                func=self._tool_browse_page,
            )
        )
        self.register(
            Tool(
                name="code_exec",
                description="Execute a short Python snippet in a temporary sandboxed directory.",
                func=self._tool_code_exec,
            )
        )
        self.register(
            Tool(
                name="read_project_file",
                description="Read a project file with safety checks.",
                func=self._tool_read_project_file,
            )
        )

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def list_tools(self) -> Dict[str, str]:
        return {name: t.description for name, t in self._tools.items()}

    async def execute(self, name: str, **kwargs: Any) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")

        result = tool.func(**kwargs)
        if isinstance(result, Awaitable):
            return await result
        return result

    # Tool implementations

    @staticmethod
    def _tool_get_time() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _tool_echo(text: Optional[str] = None) -> str:
        return text or ""

    @staticmethod
    def _tool_summarize_text(text: Optional[str] = None, max_chars: int = 200) -> str:
        if not text:
            return ""
        cleaned = text.strip()
        if len(cleaned) <= max_chars:
            return cleaned
        return cleaned[: max_chars - 3] + "..."

    @staticmethod
    def _tool_echo_with_time(text: Optional[str] = None) -> str:
        now = datetime.now(timezone.utc).isoformat()
        return f"[{now}] {text or ''}"

    @staticmethod
    def _tool_docs_search(query: str, top_k: int = 5) -> Dict[str, Any]:
        query_clean = (query or "").strip()
        if not query_clean:
            return {"query": query, "results": [], "error": "invalid query format"}

        try:
            store = DocsVectorStore()
            results = store.search(query_clean, top_k)
            if not results:
                return {"query": query, "results": [], "error": f"Documentation search returned no results for query: {query_clean}"}
            return {"query": query, "results": results, "error": None}
        except ImportError as exc:
            # Fallback to simple string-based search if ChromaDB is not available
            return ToolRegistry._tool_docs_search_fallback(query_clean, top_k)
        except Exception as exc:
            if "ChromaDB" in str(exc) or "chromadb" in str(exc).lower() or "not available" in str(exc):
                # Try fallback on ChromaDB errors
                return ToolRegistry._tool_docs_search_fallback(query_clean, top_k)
            elif "indexing" in str(exc):
                return {"query": query, "results": [], "error": "Documentation indexing in progress, please retry"}
            return {"query": query, "results": [], "error": f"Documentation search failed: {str(exc)}"}

    @staticmethod
    def _tool_docs_search_fallback(query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Fallback string-based search when ChromaDB is not available.
        """
        query_clean = (query or "").strip()
        if not query_clean:
            return {"query": query, "results": [], "error": "invalid query format"}

        docs_root = Path("docs")
        if not docs_root.exists():
            return {"query": query, "results": [], "error": "Documentation directory not found"}

        needle = query_clean.lower()
        hits: List[Dict[str, Any]] = []

        for path in docs_root.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue

            lowered = text.lower()
            if needle not in lowered:
                continue

            score = lowered.count(needle)
            idx = lowered.find(needle)
            start = max(0, idx - 120)
            end = min(len(text), idx + len(needle) + 120)
            snippet = text[start:end].strip()

            hits.append({
                "path": str(path),
                "content": snippet,
                "chunk_index": 0,
                "score": score,
                "source_reference": f"{path}#chunk-0"
            })

        hits.sort(key=lambda h: (-h["score"], h["path"]))
        results = hits[:max(0, top_k)]
        
        if not results:
            return {"query": query, "results": [], "error": f"Documentation search returned no results for query: {query_clean}"}
        return {"query": query, "results": results, "error": None}

    @staticmethod
    async def _tool_web_search(query: str, top_k: int = 5) -> Dict[str, Any]:
        query_clean = (query or "").strip()
        if not query_clean:
            return {"query": query, "results": [], "error": "invalid query format"}

        try:
            search = DuckDuckGoSearchRun()
            # DuckDuckGoSearchRun.run() returns a string with search results
            # We need to wrap the synchronous call in an async context
            import asyncio
            import re
            raw_results = await asyncio.to_thread(search.run, query_clean)
            
            # Parse the string results into structured format
            # DuckDuckGoSearchRun returns a concatenated string with date patterns like "Mar 29, 2018 ·"
            results = []
            if raw_results:
                # Split by date patterns (e.g., "Mar 29, 2018 ·", "Aug 15, 2025 ·")
                # Pattern: Month DD, YYYY · or similar date formats
                date_pattern = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}\s+·'
                snippets = re.split(date_pattern, raw_results)
                
                # Filter out empty snippets and take top_k
                # Skip first snippet if it's just intro text (usually shorter)
                start_idx = 1 if len(snippets) > 1 and len(snippets[0].strip()) < 100 else 0
                for snippet in snippets[start_idx:start_idx + top_k]:
                    snippet = snippet.strip()
                    if snippet and len(snippet) > 20:  # Filter out very short fragments
                        # Extract a title (first ~100 chars) and use full snippet
                        title = snippet[:100].strip()
                        if title.endswith("..."):
                            title = title[:-3]
                        # Clean up title - remove trailing incomplete words
                        if len(title) > 50:
                            last_space = title.rfind(' ', 0, 80)
                            if last_space > 0:
                                title = title[:last_space]
                        results.append({
                            "title": title,
                            "url": "",  # DuckDuckGoSearchRun doesn't provide URLs in the string output
                            "snippet": snippet[:500]  # Limit snippet length
                        })
                        if len(results) >= top_k:
                            break
                
                # Fallback: if no date patterns found, split by sentences or periods
                if not results:
                    # Split by double periods or long sentences
                    fallback_snippets = re.split(r'\.\s+(?=[A-Z])', raw_results)
                    for snippet in fallback_snippets[:top_k]:
                        snippet = snippet.strip()
                        if snippet and len(snippet) > 30:
                            title = snippet[:100].strip()
                            results.append({
                                "title": title,
                                "url": "",
                                "snippet": snippet[:500]
                            })
                            if len(results) >= top_k:
                                break
                
                # Last resort: return the whole result as a single snippet
                if not results and raw_results:
                    results.append({
                        "title": query_clean,
                        "url": "",
                        "snippet": raw_results[:1000]  # Limit to 1000 chars
                    })
            
            if not results:
                return {"query": query, "results": [], "error": f"Web search returned no results for query: {query_clean}"}
            return {"query": query, "results": results, "error": None}
        except httpx.HTTPError as exc:
            if hasattr(exc, "response") and exc.response.status_code == 429:
                return {"query": query, "results": [], "error": "Web search encountered rate limiting"}
            return {"query": query, "results": [], "error": f"Web search failed: network error - {str(exc)}"}
        except Exception as exc:
            if "rate limit" in str(exc).lower() or "429" in str(exc):
                return {"query": query, "results": [], "error": "Web search encountered rate limiting"}
            return {"query": query, "results": [], "error": f"Web search failed: {str(exc)}"}

    @staticmethod
    async def _tool_browse_page(url: str, max_chars: int = 4000) -> Dict[str, Any]:
        url_clean = (url or "").strip()
        if not url_clean:
            return {"url": url, "error": "empty url", "content": ""}

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url_clean)
            text = resp.text or ""
            import re
            stripped = re.sub(r"<[^>]+>", " ", text)
            stripped = re.sub(r"\s+", " ", stripped).strip()
            content = stripped[:max_chars - 3] + "..." if len(stripped) > max_chars else stripped
            return {
                "url": url_clean,
                "status_code": resp.status_code,
                "content_type": resp.headers.get("content-type", ""),
                "error": None,
                "content": content,
            }
        except Exception as exc:
            return {"url": url_clean, "error": f"fetch_failed: {str(exc)}", "content": ""}

    @staticmethod
    def _tool_code_exec(snippet: str, language: str = "python", timeout_seconds: float = 3.0) -> Dict[str, Any]:
        lang = language.lower()
        if lang != "python":
            return {"error": "unsupported language"}

        code = snippet.strip()
        if not code:
            return {"error": "empty snippet"}

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                proc = subprocess.run(
                    [sys.executable, "-c", code],
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    cwd=tmpdir,
                )
                return {
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "returncode": proc.returncode,
                    "timeout": False,
                }
            except subprocess.TimeoutExpired as exc:
                return {
                    "stdout": exc.stdout or "",
                    "stderr": exc.stderr or "",
                    "returncode": None,
                    "timeout": True,
                }
            except Exception as exc:
                return {"error": str(exc)}

    @staticmethod
    def _tool_read_project_file(path: str, max_chars: int = 2000) -> Dict[str, Any]:
        requested = Path(path).resolve()
        root = Path(".").resolve()
        try:
            requested.relative_to(root)
        except ValueError:
            return {"error": "path outside project root"}
        if not requested.is_file():
            return {"error": "file not found"}
        text = requested.read_text(encoding="utf-8")
        content = text[:max_chars - 3] + "..." if len(text) > max_chars else text
        return {"path": str(requested), "content": content}