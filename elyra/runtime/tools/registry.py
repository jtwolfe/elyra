from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from pathlib import Path
from typing import Any, Callable, Optional

from elyra.runtime.settings import get_v2_settings
from lmm.schema.bead import BeadType
from lmm.schema.delta import Provenance, ProvenanceKind
from lmm.stores.episodic import InMemoryEpisodicStore


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    name: str
    ok: bool
    result: dict[str, Any]


ToolFn = Callable[[dict[str, Any]], dict[str, Any]]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolFn] = {}

    def register(self, name: str, fn: ToolFn) -> None:
        self._tools[name] = fn

    def get(self, name: str) -> Optional[ToolFn]:
        return self._tools.get(name)


def _docs_search(args: dict[str, Any]) -> dict[str, Any]:
    """Very small local search over docs and (optionally) code.

    Args:
      query: required
      max_hits: optional (default 10)
      roots: optional list of relative roots (default: ["docs/v2", "README.md"])
    """
    query = (args.get("query") or "").strip()
    if not query:
        return {"query": query, "hits": [], "note": "empty query"}

    max_hits = int(args.get("max_hits") or 10)
    roots = args.get("roots") or ["docs/v2", "README.md"]

    repo_root = Path(__file__).resolve().parents[3]  # .../elyra/runtime/tools/registry.py -> repo root
    hits: list[dict[str, Any]] = []

    def scan_file(p: Path) -> None:
        nonlocal hits
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return
        lines = text.splitlines()
        q = query.lower()
        for idx, line in enumerate(lines, start=1):
            if q in line.lower():
                hits.append(
                    {
                        "path": str(p.relative_to(repo_root)),
                        "line": idx,
                        "text": line.strip()[:300],
                    }
                )
                if len(hits) >= max_hits:
                    return

    for root in roots:
        p = repo_root / root
        if p.is_file():
            scan_file(p)
        elif p.is_dir():
            for fp in p.rglob("*"):
                if fp.is_file() and fp.suffix.lower() in {".md", ".py", ".ts", ".tsx", ".puml"}:
                    scan_file(fp)
                    if len(hits) >= max_hits:
                        break
        if len(hits) >= max_hits:
            break

    return {"query": query, "hits": hits, "count": len(hits)}


class ToolExecutor:
    """Executes tools and records tool deltas into the episodic store."""

    def __init__(self, store: Any, registry: ToolRegistry):
        self._store = store
        self._registry = registry

    def execute(
        self,
        calls: list[ToolCall] | list[dict[str, Any]],
        *,
        episode_id: str | None = None,
        knot_id: str | None = None,
        microagent_bead_ref: dict[str, Any] | None = None,
        tool_bead_refs: dict[str, dict[str, Any]] | None = None,
    ) -> list[ToolResult] | list[dict[str, Any]]:
        results: list[ToolResult] = []
        typed_calls: list[ToolCall] = []
        for c in calls:
            if isinstance(c, ToolCall):
                typed_calls.append(c)
            else:
                typed_calls.append(ToolCall(name=str(c.get("name") or ""), args=dict(c.get("args") or {})))

        for c in typed_calls:
            call_delta = self._store.append_tool_call_delta(
                tool_name=c.name,
                args=c.args,
                provenance_kind=ProvenanceKind.system,
                episode_id=episode_id,
                knot_id=knot_id,
                microagent_bead_ref=microagent_bead_ref,
                tool_bead_ref=(tool_bead_refs or {}).get(c.name),
            )
            fn = self._registry.get(c.name)
            if fn is None:
                tr = ToolResult(
                    name=c.name,
                    ok=False,
                    result={
                        "error": {"kind": "unknown_tool", "message": f"Unknown tool: {c.name}"},
                        "call_id": call_delta.id,
                        "duration_ms": 0,
                    },
                )
                self._store.append_tool_result_delta(
                    tool_name=c.name,
                    result=tr.result,
                    ok=False,
                    provenance_kind=ProvenanceKind.system,
                    episode_id=episode_id,
                    knot_id=knot_id,
                    microagent_bead_ref=microagent_bead_ref,
                    tool_bead_ref=(tool_bead_refs or {}).get(c.name),
                )
                results.append(tr)
                continue

            try:
                t0 = perf_counter()
                r = fn(c.args)
                dt_ms = int((perf_counter() - t0) * 1000)
                wrapped = {"data": r, "call_id": call_delta.id, "duration_ms": dt_ms}
                tr = ToolResult(name=c.name, ok=True, result=wrapped)
                self._store.append_tool_result_delta(
                    tool_name=c.name,
                    result=wrapped,
                    ok=True,
                    provenance_kind=ProvenanceKind.system,
                    episode_id=episode_id,
                    knot_id=knot_id,
                    microagent_bead_ref=microagent_bead_ref,
                    tool_bead_ref=(tool_bead_refs or {}).get(c.name),
                )
                results.append(tr)
            except Exception as exc:
                tr = ToolResult(
                    name=c.name,
                    ok=False,
                    result={
                        "error": {"kind": "exception", "message": str(exc)},
                        "call_id": call_delta.id,
                        "duration_ms": 0,
                    },
                )
                self._store.append_tool_result_delta(
                    tool_name=c.name,
                    result=tr.result,
                    ok=False,
                    provenance_kind=ProvenanceKind.system,
                    episode_id=episode_id,
                    knot_id=knot_id,
                    microagent_bead_ref=microagent_bead_ref,
                    tool_bead_ref=(tool_bead_refs or {}).get(c.name),
                )
                results.append(tr)

        # Maintain compatibility with the LCM adapter: if input was dicts, output dicts.
        if calls and not isinstance(calls[0], ToolCall):
            return [{"name": r.name, "ok": r.ok, "result": r.result} for r in results]
        return results


class SemanticBeadAccessor:
    """Minimal accessor for semantic beads stored as memory_bead versions.

    v0: retrieves latest N semantic bead versions from the episodic store.
    """

    def __init__(self, store: Any):
        self._store = store

    def get_recent_semantic(self, limit: int) -> list[dict[str, Any]]:
        rows = self._store.get_recent_bead_versions(bead_type=BeadType.memory_bead, limit=limit)
        # Filter for our current semantic bead convention.
        out: list[dict[str, Any]] = []
        for r in rows:
            data = r.get("data") or {}
            if data.get("kind") in {"semantic_turn_summary", "semantic_fact"}:
                # Attach decayed trust score if present (read-time; does not mutate store).
                try:
                    from elyra.runtime.settings import get_v2_settings
                    from elyra.runtime.trust import TrustEngine
                    from lmm.schema.delta import ProvenanceKind

                    trust = dict(data.get("trust") or {})
                    if trust.get("score") is not None and trust.get("created_ts"):
                        settings = get_v2_settings()
                        engine = TrustEngine(
                            promote_threshold=settings.TRUST_PROMOTE_THRESHOLD,
                            half_life_seconds=settings.TRUST_DECAY_HALF_LIFE_SECONDS,
                            provenance_weights_json=settings.TRUST_PROVENANCE_WEIGHTS_JSON,
                        )
                        decayed = engine.decay_score(
                            float(trust.get("score") or 0.0),
                            created_ts=str(trust.get("created_ts")),
                            now_ts=datetime.now(timezone.utc).isoformat(),
                        )
                        trust["decayed_score"] = max(0.0, min(1.0, float(decayed)))
                        trust["provenance"] = str(ProvenanceKind.system.value)
                        data["trust"] = trust
                        r["data"] = data
                except Exception:
                    pass
                out.append(r)
        return out[-limit:]


class LCMToolExecutorAdapter:
    """Adapter to satisfy LCM's minimal ToolExecutor protocol.

    LCM expects: execute([{name, args}, ...]) -> [{name, ok, result}, ...]
    Elyra tool executor uses typed ToolCall/ToolResult.
    """

    def __init__(self, inner: ToolExecutor):
        self._inner = inner

    def execute(self, calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        typed = [ToolCall(name=str(c.get("name") or ""), args=dict(c.get("args") or {})) for c in calls]
        results = self._inner.execute(typed)
        return [{"name": r.name, "ok": r.ok, "result": r.result} for r in results]


def build_default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register("docs_search", _docs_search)
    # Web search is optional; keep disabled by default so offline tests remain hermetic.
    if get_v2_settings().ENABLE_WEB_SEARCH:
        try:
            from ddgs import DDGS  # type: ignore

            def _web_search(args: dict[str, Any]) -> dict[str, Any]:
                q = (args.get("query") or "").strip()
                if not q:
                    return {"query": q, "hits": [], "note": "empty query"}
                max_results = int(args.get("max_results") or 5)
                with DDGS() as ddgs:
                    hits = list(ddgs.text(q, max_results=max_results))
                return {"query": q, "hits": hits, "count": len(hits)}

            reg.register("web_search", _web_search)
        except Exception:
            # If ddgs isn't available in the environment, silently skip registration.
            pass
    return reg


