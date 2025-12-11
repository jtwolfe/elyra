from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import DefaultDict, Dict, List, Tuple

from langchain_core.messages import BaseMessage

from elyra_backend.config import settings


class HippocampalSim:
    """
    In-memory stub implementation of the HippocampalSim interface.

    This version does not talk to Redis, Neo4j, or Qdrant. It simply keeps
    recent messages in-process so that the rest of the Elyra stack can be
    developed and tested.

    For Phase 1, it also maintains a *very small* JSON-backed episodic log so
    that basic memory survives process restarts. This is intentionally minimal
    and not a replacement for the full Redis/Neo4j/Qdrant stack.
    """

    system_prompt: str = (
        "I am Elyra, a memory-driven AI assistant. "
        "I only see a curated slice of your history, not the full raw log. "
        "I have access to tools including web_search (for internet searches), "
        "docs_search (for project documentation), get_time (for current time), "
        "browse_page (for fetching web pages), and others. "
        "I may collaborate with internal sub-agents (such as a researcher and a "
        "validator) and call tools when useful to better answer your questions. "
        "When tool outputs are provided below, I use them to answer accurately. "
        "I will be concise, helpful, and honest about what I know and what I do "
        "not know."
    )

    def __init__(self) -> None:
        # Keyed by (user_id, project_id)
        self._episodes: DefaultDict[Tuple[str, str], List[Dict[str, str]]] = (
            defaultdict(list)
        )
        # Very small JSON file for persistence across restarts.
        self._storage_path = Path("data/hippocampal_episodes.json")
        if settings.ENABLE_PERSISTENT_EPISODES:
            self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load previously stored episodes from disk, if present."""
        if not settings.ENABLE_PERSISTENT_EPISODES:
            return
        try:
            if not self._storage_path.exists():
                return
            raw = self._storage_path.read_text(encoding="utf-8")
            if not raw.strip():
                return
            payload: Dict[str, List[Dict[str, str]]] = json.loads(raw)
            for key_str, episodes in payload.items():
                user_id, project_id = key_str.split("::", 1)
                self._episodes[(user_id, project_id)].extend(episodes)
        except Exception:
            # If anything goes wrong while loading, fall back to an empty store.
            self._episodes = defaultdict(list)

    def _save_to_disk(self) -> None:
        """Persist the current episodic buffer to a small JSON file."""
        if not settings.ENABLE_PERSISTENT_EPISODES:
            return
        try:
            if not self._episodes:
                return
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            payload: Dict[str, List[Dict[str, str]]] = {}
            for (user_id, project_id), episodes in self._episodes.items():
                key_str = f"{user_id}::{project_id}"
                payload[key_str] = episodes
            self._storage_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            # Persistence is best-effort only for Phase 1.
            return

    async def recall(self, prompt: str, user_id: str, project_id: str) -> Tuple[str, float]:
        """
        Return a small curated text context based on the last few stored messages,
        along with an adequacy score (0.0-1.0) indicating how relevant/complete
        the context is for the given prompt.

        In a full implementation this would query Redis/Neo4j/Qdrant.
        """
        key = (user_id, project_id)
        history = self._episodes.get(key, [])
        if not history:
            return ("No prior episodic context is available yet.", 0.0)

        # Separate recent user questions and assistant replies. This is a very
        # small heuristic standing in for the richer KG + vector store design.
        recent = history[-10:]
        user_q: List[str] = []
        assistant_a: List[str] = []
        for e in recent:
            role = e.get("role") or ""
            content = e.get("content", "").strip()
            if not content:
                continue
            if role == "user":
                user_q.append(content)
            elif role == "assistant":
                assistant_a.append(content)

        def _format_block(title: str, items: List[str]) -> str:
            if not items:
                return f"{title}:\n- (none yet)"
            # Keep the context compact by only inlining a few recent lines.
            tail = items[-3:]
            joined = "\n".join(f"- {c}" for c in tail)
            return f"{title}:\n{joined}"

        user_block = _format_block("Recent user questions", user_q)
        asst_block = _format_block("Recent assistant replies", assistant_a)
        context_text = f"{user_block}\n\n{asst_block}"

        # Simple adequacy score: normalize the number of relevant context lines
        # to a 0.0-1.0 scale. This is a placeholder for richer semantic scoring.
        relevant_lines = len(user_q) + len(assistant_a)
        adequacy_score = min(1.0, relevant_lines / 10.0)

        return (context_text, adequacy_score)

    async def generate_thought(self, user_id: str, project_id: str) -> str:
        """
        Generate a very simple internal thought string.

        Later phases will use EchoReplay and more advanced logic here.
        """
        return (
            "Internal thought: consider how this message fits into the user's "
            "ongoing projects, but avoid speculating beyond the given context."
        )

    async def ingest(
        self,
        event: BaseMessage,
        user_id: str,
        project_id: str,
        thought: str,
    ) -> None:
        """
        Store the message as a new episode.

        The `thought` parameter is currently unused but included to match the
        intended interface.
        """
        key = (user_id, project_id)
        # Try to infer a simple role string from the message type.
        msg_type = getattr(event, "type", "")
        role = "assistant" if msg_type == "ai" else "user" if msg_type == "human" else ""
        content = getattr(event, "content", "")
        # Extremely small keyword-based tagging for later filtering/debugging.
        lowered = str(content).lower()
        tags: List[str] = []
        for kw in ("memory", "tool", "research", "roadmap", "code"):
            if kw in lowered:
                tags.append(kw)

        episode = {
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "thought": thought,
            "role": role,
            "tags": tags,
        }
        self._episodes[key].append(episode)
        # Best-effort persistence; failures are ignored.
        self._save_to_disk()


