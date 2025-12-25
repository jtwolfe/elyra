from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4

from lmm.schema.bead import BeadRef, BeadType
from lmm.schema.delta import DeltaKind, GenericDelta, Provenance, ProvenanceKind


class LLMClient(Protocol):
    def chat_json(self, messages: list[dict[str, Any]]) -> dict[str, Any]: ...


class ToolExecutor(Protocol):
    def execute(
        self,
        calls: list[dict[str, Any]],
        *,
        episode_id: str | None = None,
        knot_id: str | None = None,
        microagent_bead_ref: dict[str, Any] | None = None,
        tool_bead_refs: dict[str, dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]: ...


@dataclass
class MicroagentResult:
    microagent_bead_ref: BeadRef
    planned_tool_calls: list[dict[str, Any]]
    executed_tools: list[dict[str, Any]]


class MicroagentRunner:
    """Runs a single microagent loop to select and execute tool calls."""

    def __init__(self, *, llm: LLMClient, tool_executor: ToolExecutor, store: Any):
        self._llm = llm
        self._tool_executor = tool_executor
        self._store = store

    def run(
        self,
        *,
        braid_id: str,
        knot_id: str,
        episode_id: str,
        goal: str,
        allowed_tools: list[str],
        tool_bead_refs: dict[str, BeadRef],
        ribbon: dict[str, Any],
    ) -> MicroagentResult:
        microagent_bead_id = f"microagent:{knot_id}:{uuid4()}"
        microagent_bead = {
            "kind": "tool_microagent",
            "knot_id": knot_id,
            "goal": goal,
            "allowed_tools": list(allowed_tools),
        }
        bead_ref = self._store.upsert_bead_version(
            bead_id=microagent_bead_id, bead_type=BeadType.microagent_bead, data=microagent_bead
        )

        # Record microagent start delta
        self._store.append_delta(
            GenericDelta(
                id=str(uuid4()),
                braid_id=braid_id,
                kind=DeltaKind.microagent,
                provenance=Provenance(kind=ProvenanceKind.system, episode_id=episode_id, knot_id=knot_id),
                confidence=0.55,
                payload={"event": "microagent_spawn", "bead_ref": bead_ref.model_dump()},
            )
        )

        prompt = [
            {
                "role": "system",
                "content": (
                    "I am Elyra (Braid v2). I am in MICROAGENT tool-selection.\n"
                    "Rules:\n"
                    "- I only output valid JSON.\n"
                    "- I only select tools from the allowed list.\n"
                    "- I only propose tools that are necessary to satisfy the goal.\n"
                    "JSON schema:\n"
                    '{ "tool_calls": [{"name": string, "args": object}], "notes": string }\n'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Goal:\n{goal}\n\n"
                    f"Allowed tools:\n{allowed_tools}\n\n"
                    f"Context ribbon (JSON):\n{ribbon}\n"
                ),
            },
        ]
        plan = self._llm.chat_json(prompt)
        planned_calls = list(plan.get("tool_calls") or [])
        # Enforce allowlist
        planned_calls = [c for c in planned_calls if str((c or {}).get("name") or "") in set(allowed_tools)]

        tool_refs_map = {name: ref.model_dump() for name, ref in tool_bead_refs.items()}
        executed = self._tool_executor.execute(
            planned_calls,
            episode_id=episode_id,
            knot_id=knot_id,
            microagent_bead_ref=bead_ref.model_dump(),
            tool_bead_refs=tool_refs_map,
        )
        return MicroagentResult(
            microagent_bead_ref=bead_ref,
            planned_tool_calls=planned_calls,
            executed_tools=executed,
        )


