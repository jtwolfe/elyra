from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from lmm.schema.bead import BeadType


@dataclass(frozen=True)
class SemanticBeadWrite:
    bead_id: str
    data: dict[str, Any]


class SemanticConsolidator:
    """Very small semantic consolidator (Phase 2 v0).

    v0 behavior:
    - writes a single semantic memory bead per knot that summarizes the last turn
    - links to evidence via delta ids

    This is intentionally conservative and deterministic; richer extraction (facts, entities)
    can be added later via an LLM microagent.
    """

    def propose_turn_summary(
        self,
        *,
        user_text: str,
        assistant_text: str,
        evidence_delta_ids: list[str],
        knot_id: str,
    ) -> SemanticBeadWrite:
        bead_id = f"semantic:{knot_id}:{uuid4()}"
        data = {
            "kind": "semantic_turn_summary",
            "knot_id": knot_id,
            "user_text": user_text,
            "assistant_text": assistant_text,
            "evidence_delta_ids": list(evidence_delta_ids),
        }
        return SemanticBeadWrite(bead_id=bead_id, data=data)

    @property
    def bead_type(self) -> BeadType:
        return BeadType.memory_bead


