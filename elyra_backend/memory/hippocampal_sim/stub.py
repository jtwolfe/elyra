from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import DefaultDict, Dict, List, Tuple

from langchain_core.messages import BaseMessage


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
        "You are Elyra, a memory-driven AI assistant. "
        "You see only a curated slice of the user's history, "
        "not the full raw log. Be concise, helpful, and honest."
    )

    def __init__(self) -> None:
        # Keyed by (user_id, project_id)
        self._episodes: DefaultDict[Tuple[str, str], List[Dict[str, str]]] = (
            defaultdict(list)
        )
        # Very small JSON file for persistence across restarts.
        self._storage_path = Path("data/hippocampal_episodes.json")
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load previously stored episodes from disk, if present."""
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
        try:
            if not self._episodes:
                return
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            payload: Dict[str, List[Dict[str, str]]] = {}
            for (user_id, project_id), episodes in self._episodes.items():
                key_str = f"{user_id}::${project_id}"
                payload[key_str] = episodes
            self._storage_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            # Persistence is best-effort only for Phase 1.
            return

    async def recall(self, prompt: str, user_id: str, project_id: str) -> str:
        """
        Return a trivial text context based on the last few stored messages.

        In a full implementation this would query Redis/Neo4j/Qdrant.
        """
        key = (user_id, project_id)
        history = self._episodes.get(key, [])
        if not history:
            return "No prior episodic context is available yet."

        # Take the last few episodes and inline their content.
        tail = history[-3:]
        joined = "\n".join(
            f"- {e.get('content', '')}" for e in tail if e.get("content", "")
        )
        return f"Recent context:\n{joined}"

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
        Store the assistant message as a new episode.

        The `thought` parameter is currently unused but included to match the
        intended interface.
        """
        key = (user_id, project_id)
        episode = {
            "content": getattr(event, "content", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "thought": thought,
        }
        self._episodes[key].append(episode)
        # Best-effort persistence; failures are ignored.
        self._save_to_disk()


