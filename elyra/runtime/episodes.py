from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from lmm.schema.episode import Episode, EpisodeEdge, EpisodeEdgeType, EpisodeState


@dataclass
class ForkProposal:
    should_fork: bool
    confidence: float
    reason: str
    candidate_labels: dict[str, Any]


class EpisodeManager:
    """Composition-layer episode/fork manager (Phase 3 v0)."""

    def __init__(self, store: Any):
        self._store = store

    def ensure_active_episode(self, braid_id: str) -> Episode:
        active = self._store.get_active_episode()
        if active is not None:
            return active
        ep = Episode(
            id=f"episode:{uuid4()}",
            braid_id=braid_id,
            state=EpisodeState.active,
            labels={"topics": [], "intents": [], "modalities": []},
            summary_cache={"created_ts": datetime.now(timezone.utc).isoformat()},
        )
        self._store.upsert_episode(ep)
        self._store.set_active_episode_id(ep.id)
        return ep

    def propose_fork_pending(
        self, *, parent: Episode, proposal: ForkProposal, now_ts: Optional[str] = None
    ) -> Optional[Episode]:
        if not proposal.should_fork:
            return None
        now = now_ts or datetime.now(timezone.utc).isoformat()
        labels = proposal.candidate_labels or {"topics": [], "intents": [], "modalities": []}
        existing = self.find_matching_pending(parent_episode_id=parent.id, labels=labels)
        if existing is not None:
            cache = dict(existing.summary_cache or {})
            cache["last_seen_ts"] = now
            cache["confirmation_count"] = int(cache.get("confirmation_count") or 0) + 1
            cache["fork_reason"] = proposal.reason or cache.get("fork_reason") or ""
            cache["fork_confidence"] = max(float(cache.get("fork_confidence") or 0.0), proposal.confidence)
            existing.summary_cache = cache
            self._store.upsert_episode(existing)
            return existing

        ep = Episode(
            id=f"episode:{uuid4()}",
            braid_id=parent.braid_id,
            state=EpisodeState.fork_pending,
            labels=labels,
            edges=[
                EpisodeEdge(type=EpisodeEdgeType.forked_from, to_episode_id=parent.id, confidence=proposal.confidence)
            ],
            summary_cache={
                "created_ts": now,
                "last_seen_ts": now,
                "pending_knot_count": 0,
                "confirmation_count": 1,
                "fork_reason": proposal.reason,
                "fork_confidence": proposal.confidence,
                "parent_episode_id": parent.id,
            },
        )
        self._store.upsert_episode(ep)
        return ep

    def find_matching_pending(self, *, parent_episode_id: str, labels: dict[str, Any]) -> Optional[Episode]:
        """Find an existing fork_pending episode with the same parent + labels."""
        try:
            pending = self._store.list_episodes(state=EpisodeState.fork_pending, limit=50)
        except Exception:
            return None
        for ep in pending:
            cache = ep.summary_cache or {}
            if cache.get("parent_episode_id") != parent_episode_id:
                continue
            if (ep.labels or {}) == (labels or {}):
                return ep
        return None

    def tick_fork_pending(self, episode_id: str, *, now_ts: Optional[str] = None) -> dict[str, Any]:
        now = now_ts or datetime.now(timezone.utc).isoformat()
        ep = self._store.get_episode(episode_id)
        if ep is None:
            return {"status": "missing"}
        cache = dict(ep.summary_cache or {})
        cache["last_seen_ts"] = now
        cache["pending_knot_count"] = int(cache.get("pending_knot_count") or 0) + 1
        ep.summary_cache = cache
        self._store.upsert_episode(ep)
        return {
            "status": "ticked",
            "pending_knot_count": cache["pending_knot_count"],
            "confirmation_count": int(cache.get("confirmation_count") or 0),
        }

    def promote_fork(self, episode_id: str) -> Optional[Episode]:
        ep = self._store.get_episode(episode_id)
        if ep is None:
            return None
        ep.state = EpisodeState.active
        self._store.upsert_episode(ep)
        self._store.set_active_episode_id(ep.id)
        return ep

    def attach_continuity_snapshot(self, episode_id: str, snapshot: dict[str, Any]) -> None:
        """Store a continuity buffer snapshot on an episode (best-effort)."""
        ep = self._store.get_episode(episode_id)
        if ep is None:
            return
        cache = dict(ep.summary_cache or {})
        cache["continuity"] = snapshot
        ep.summary_cache = cache
        self._store.upsert_episode(ep)

    def expire_episode(self, episode_id: str) -> Optional[Episode]:
        ep = self._store.get_episode(episode_id)
        if ep is None:
            return None
        ep.state = EpisodeState.expired
        self._store.upsert_episode(ep)
        return ep


