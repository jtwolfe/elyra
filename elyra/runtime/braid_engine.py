from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from lcm.orchestrator.knot_processor import KnotProcessor, KnotRequest
from lmm.retrieval.ribbon import InMemoryRibbonBuilder
from lmm.schema.delta import DeltaKind, GenericDelta, Provenance, ProvenanceKind
from lmm.stores.episodic import InMemoryEpisodicStore


@dataclass
class BraidTurnResult:
    response_text: str
    thought_narrative: str
    trace: dict[str, Any]


class _RibbonProviderAdapter:
    def __init__(self, store: InMemoryEpisodicStore, ribbon_builder: InMemoryRibbonBuilder):
        self._store = store
        self._builder = ribbon_builder

    def build_ribbon(self, max_messages: int) -> dict[str, Any]:
        ribbon = self._builder.build(self._store.deltas, self._store.knots, max_messages=max_messages)
        return {
            "recent_messages": ribbon.recent_messages,
            "stats": {"knot_count": ribbon.knot_count, "delta_count": ribbon.delta_count},
        }


class BraidEngine:
    """Minimal runnable Braid v2 engine (in-memory skeleton).

    - appends message deltas
    - runs LCM knot processor (think/speak)
    - stores thought summary bead
    - commits a knot over delta range
    - returns a UI-friendly trace payload
    """

    def __init__(self, braid_id: str):
        self.braid_id = braid_id
        self.primary_episode_id = f"session-{datetime.now(timezone.utc).date().isoformat()}"

        self.store = InMemoryEpisodicStore(braid_id=braid_id)
        self.ribbon_builder = InMemoryRibbonBuilder()
        self.knot_processor = KnotProcessor(_RibbonProviderAdapter(self.store, self.ribbon_builder))

    def handle_user_message(self, user_message: str) -> BraidTurnResult:
        # Append user message delta
        user_delta = self.store.append_message_delta("user", user_message, ProvenanceKind.user)
        start_delta_id = user_delta.id

        # Run cognition (think/speak inside KnotProcessor)
        req = KnotRequest(
            braid_id=self.braid_id,
            primary_episode_id=self.primary_episode_id,
            user_message=user_message,
        )
        result = self.knot_processor.run(req)

        # Store thought summary as a bead (narrative + structured)
        thought_ref = self.store.upsert_reasoning_summary_bead(
            narrative=result.thought_narrative,
            structured=result.thought_structured,
        )
        self.store.append_delta(
            GenericDelta(
                id=str(uuid4()),
                braid_id=self.braid_id,
                kind=DeltaKind.bead_write,
                provenance=Provenance(kind=ProvenanceKind.system),
                confidence=0.6,
                payload={"bead_ref": thought_ref.model_dump()},
            )
        )

        # Append assistant message delta
        assistant_delta = self.store.append_message_delta(
            "assistant", result.response_text, ProvenanceKind.assistant
        )
        end_delta_id = assistant_delta.id

        # Commit knot
        knot = self.store.commit_knot(
            primary_episode_id=self.primary_episode_id,
            start_delta_id=start_delta_id,
            end_delta_id=end_delta_id,
            start_ts=result.start_ts,
            end_ts=result.end_ts,
            summary="Responded to user message (v2 skeleton).",
            thought_summary_bead_ref=thought_ref,
            planned_tools=result.planned_tools,
            executed_tools=result.executed_tools,
        )

        trace = {
            "knot": knot.model_dump(),
            "deltas": [d.model_dump() for d in self.store.deltas[-25:]],
        }

        return BraidTurnResult(
            response_text=result.response_text,
            thought_narrative=result.thought_narrative,
            trace=trace,
        )


