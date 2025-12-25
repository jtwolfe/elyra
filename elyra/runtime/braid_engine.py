from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from lcm.orchestrator.knot_processor import KnotProcessor, KnotRequest, KnotResult
from lcm.testing.harness import MVPSafeTestHarness
from lmm.retrieval.ribbon import InMemoryRibbonBuilder
from lmm.schema.bead import BeadType
from lmm.schema.delta import DeltaKind, GenericDelta, Provenance, ProvenanceKind
from lmm.stores.episodic import InMemoryEpisodicStore
from lmm.stores.neo4j_episodic import Neo4jEpisodicStore

from elyra.llm.mock_client import MockLLMClient
from elyra.llm.ollama_router import OllamaRouterClient
from elyra.runtime.settings import get_v2_settings
from elyra.runtime.tools.registry import ToolExecutor, SemanticBeadAccessor, build_default_registry
from elyra.runtime.consolidation.semantic import SemanticConsolidator
from elyra.runtime.episodes import EpisodeManager, ForkProposal
from elyra.runtime.trust import TrustEngine
from elyra.runtime.vector.qdrant_semantic import QdrantSemanticIndex
from elyra.runtime.microagents.runner import MicroagentRunner


@dataclass
class BraidTurnResult:
    response_text: str
    thought_narrative: str
    trace: dict[str, Any]


class _RibbonProviderAdapter:
    def __init__(self, store: Any, ribbon_builder: InMemoryRibbonBuilder, semantic_index: QdrantSemanticIndex | None):
        self._store = store
        self._builder = ribbon_builder
        self._semantic_index = semantic_index

    def build_ribbon(self, max_messages: int) -> dict[str, Any]:
        settings = get_v2_settings()
        deltas = self._store.get_recent_deltas(settings.RIBBON_MAX_DELTAS)
        knots = self._store.get_recent_knots(settings.RIBBON_MAX_KNOTS)
        ribbon = self._builder.build(deltas, knots, max_messages=max_messages)
        # Prefer Qdrant semantic recall (top-K relevant) when enabled.
        semantic: list[dict[str, Any]] = []
        if self._semantic_index is not None and ribbon.recent_messages:
            # Use latest user message as query (user delta is appended before ribbon is built).
            q = ""
            for m in reversed(ribbon.recent_messages):
                if (m or {}).get("role") == "user":
                    q = str((m or {}).get("content") or "")
                    break
            hits = self._semantic_index.search(query=q, top_k=settings.QDRANT_TOP_K)
            semantic = [{"score": h.score, "data": h.payload} for h in hits]
        else:
            semantic = SemanticBeadAccessor(self._store).get_recent_semantic(settings.RIBBON_MAX_SEMANTIC_BEADS)
        return {
            "recent_messages": ribbon.recent_messages,
            "stats": {"knot_count": ribbon.knot_count, "delta_count": ribbon.delta_count},
            "semantic_recent": semantic,
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

        settings = get_v2_settings()
        if settings.PERSISTENCE_BACKEND.lower().strip() == "neo4j":
            self.store = Neo4jEpisodicStore(
                braid_id=braid_id,
                uri=settings.NEO4J_URI,
                user=settings.NEO4J_USER,
                password=settings.NEO4J_PASSWORD,
            )
        else:
            self.store = InMemoryEpisodicStore(braid_id=braid_id)
        self.ribbon_builder = InMemoryRibbonBuilder()
        self._semantic_index: QdrantSemanticIndex | None = None
        if settings.ENABLE_QDRANT:
            try:
                self._semantic_index = QdrantSemanticIndex(
                    qdrant_url=settings.QDRANT_URL,
                    braid_id=braid_id,
                    embedding_model_name=settings.EMBEDDING_MODEL_NAME,
                )
            except Exception:
                self._semantic_index = None

        # LLM backend selection (ollama vs offline mock)
        if settings.LLM_BACKEND.lower().strip() == "mock":
            llm = MockLLMClient()
        else:
            llm = OllamaRouterClient()

        # Tools registry + executor (invoked by microagents only)
        self._registry = build_default_registry()
        self._tool_executor = ToolExecutor(self.store, self._registry)

        # MVP-safe test harness (non-fatal stubs)
        test_harness = MVPSafeTestHarness()

        self.knot_processor = KnotProcessor(
            _RibbonProviderAdapter(self.store, self.ribbon_builder, self._semantic_index),
            llm=llm,
            tool_executor=None,
            test_harness=test_harness,
        )
        self._microagent_runner = MicroagentRunner(llm=llm, tool_executor=self._tool_executor, store=self.store)
        self._semantic_consolidator = SemanticConsolidator()
        self._episode_manager = EpisodeManager(self.store)
        self._active_episode = self._episode_manager.ensure_active_episode(braid_id)
        self._last_dream_knot_id: str | None = None
        self._last_metacog_knot_id: str | None = None

        # Ensure tool beads exist (tool_bead versions are stable references for auditing).
        self._tool_bead_refs: dict[str, Any] = {}
        for name in sorted(self._registry._tools.keys()):  # type: ignore[attr-defined]
            try:
                ref = self.store.upsert_bead_version(
                    bead_id=f"tool:{name}",
                    bead_type=BeadType.tool_bead,
                    data={"kind": "tool_bead", "name": name},
                )
                self._tool_bead_refs[name] = ref
            except Exception:
                continue

    def _get_metacog_fork_params(self) -> dict[str, Any]:
        """Best-effort read of latest metacognition params from memory beads."""
        try:
            rows = self.store.get_recent_bead_versions(bead_type=BeadType.memory_bead, limit=50)
            for r in reversed(rows):
                data = r.get("data") or {}
                if data.get("kind") == "metacog_fork_params":
                    params = data.get("params") or {}
                    if isinstance(params, dict):
                        return params
        except Exception:
            pass
        return {}

    def dream_tick(self) -> None:
        """Phase 5 (v0): deterministic dream replay -> writes a low-trust memory bead."""
        settings = get_v2_settings()
        try:
            knots = self.store.get_recent_knots(1)
            if not knots:
                return
            knot = knots[-1]
            if self._last_dream_knot_id == knot.id:
                return
            self._last_dream_knot_id = knot.id

            # Find latest semantic turn summary (if any) and "replay" it.
            rows = self.store.get_recent_bead_versions(bead_type=BeadType.memory_bead, limit=50)
            latest_sem = None
            for r in reversed(rows):
                d = (r.get("data") or {})
                if d.get("kind") == "semantic_turn_summary":
                    latest_sem = d
                    break
            replay = {
                "kind": "dream_replay",
                "knot_id": knot.id,
                "note": "Deterministic replay of the latest turn summary (v0).",
                "user_text": (latest_sem or {}).get("user_text"),
                "assistant_text": (latest_sem or {}).get("assistant_text"),
            }

            engine = TrustEngine(
                promote_threshold=settings.TRUST_PROMOTE_THRESHOLD,
                half_life_seconds=settings.TRUST_DECAY_HALF_LIFE_SECONDS,
                provenance_weights_json=settings.TRUST_PROVENANCE_WEIGHTS_JSON,
            )
            evidence = self.store.get_recent_deltas(10)
            trust = engine.score_for_bead(
                evidence_deltas=evidence,
                tests=[],
                provenance_kind=ProvenanceKind.dream,
            )
            replay["trust"] = {
                "score": trust.score,
                "decayed_score": trust.decayed_score,
                "state": trust.state,
                "created_ts": trust.details.get("created_ts"),
                "details": trust.details,
            }

            bead_id = f"dream:{knot.id}:{uuid4()}"
            ref = self.store.upsert_bead_version(bead_id=bead_id, bead_type=BeadType.memory_bead, data=replay)
            self.store.append_delta(
                GenericDelta(
                    id=str(uuid4()),
                    braid_id=self.braid_id,
                    kind=DeltaKind.bead_write,
                    provenance=Provenance(kind=ProvenanceKind.dream, knot_id=knot.id, episode_id=self._active_episode.id),
                    confidence=float(trust.score),
                    payload={"bead_ref": ref.model_dump(), "kind": "dream_replay"},
                )
            )
        except Exception as exc:
            # Never fatal; record as observation for UI.
            try:
                self.store.append_delta(
                    GenericDelta(
                        id=str(uuid4()),
                        braid_id=self.braid_id,
                        kind=DeltaKind.observation,
                        provenance=Provenance(kind=ProvenanceKind.dream),
                        confidence=0.3,
                        payload={"error": {"message": str(exc), "where": "dream_tick"}},
                    )
                )
            except Exception:
                pass

    def metacog_tick(self) -> None:
        """Phase 5 (v0): tune fork parameters based on recent trust/tests."""
        settings = get_v2_settings()
        try:
            knots = self.store.get_recent_knots(1)
            if not knots:
                return
            knot = knots[-1]
            if self._last_metacog_knot_id == knot.id:
                return
            self._last_metacog_knot_id = knot.id

            recent_deltas = self.store.get_recent_deltas(settings.TRACE_MAX_DELTAS)
            trust_d = [d for d in recent_deltas if d.kind == DeltaKind.trust]
            trust_scores = []
            for d in trust_d[-settings.METACOG_WINDOW_TURNS :]:
                t = (d.payload or {}).get("trust") or {}
                if isinstance(t, dict) and t.get("score") is not None:
                    trust_scores.append(float(t.get("score") or 0.0))
            avg_trust = (sum(trust_scores) / len(trust_scores)) if trust_scores else 0.6

            # Use recent reasoning bead versions to compute test pass-rate.
            rows = self.store.get_recent_bead_versions(bead_type=BeadType.reasoning_bead, limit=20)
            tests_seen = []
            for r in rows:
                structured = (r.get("data") or {}).get("structured") or {}
                for t in (structured.get("tests") or []):
                    if isinstance(t, dict):
                        tests_seen.append(t)
            pass_rate = 1.0
            if tests_seen:
                passed = sum(1 for t in tests_seen if bool(t.get("passed", True)))
                pass_rate = passed / len(tests_seen)

            # Heuristic tuning (v0): more conservative when trust/tests look weak.
            confirmation_required = int(settings.FORK_CONFIRMATION_REQUIRED)
            ttl_knots = int(settings.FORK_PENDING_TTL_KNOTS)
            if avg_trust < 0.55 or pass_rate < 0.8:
                confirmation_required = min(4, confirmation_required + 1)
                ttl_knots = min(20, ttl_knots + 2)
            elif avg_trust > 0.8 and pass_rate > 0.95:
                confirmation_required = max(1, confirmation_required - 1)
                ttl_knots = max(4, ttl_knots - 1)

            bead = {
                "kind": "metacog_fork_params",
                "knot_id": knot.id,
                "params": {
                    "confirmation_required": confirmation_required,
                    "pending_ttl_knots": ttl_knots,
                },
                "signals": {"avg_trust": avg_trust, "test_pass_rate": pass_rate, "tests_seen": len(tests_seen)},
            }
            bead_id = f"metacog:{knot.id}:{uuid4()}"
            ref = self.store.upsert_bead_version(bead_id=bead_id, bead_type=BeadType.memory_bead, data=bead)
            self.store.append_delta(
                GenericDelta(
                    id=str(uuid4()),
                    braid_id=self.braid_id,
                    kind=DeltaKind.microagent,
                    provenance=Provenance(kind=ProvenanceKind.system, knot_id=knot.id, episode_id=self._active_episode.id),
                    confidence=0.6,
                    payload={"kind": "metacog_tick", "bead_ref": ref.model_dump()},
                )
            )
        except Exception as exc:
            try:
                self.store.append_delta(
                    GenericDelta(
                        id=str(uuid4()),
                        braid_id=self.braid_id,
                        kind=DeltaKind.observation,
                        provenance=Provenance(kind=ProvenanceKind.system),
                        confidence=0.3,
                        payload={"error": {"message": str(exc), "where": "metacog_tick"}},
                    )
                )
            except Exception:
                pass

    def handle_user_message(self, user_message: str) -> BraidTurnResult:
        settings = get_v2_settings()
        # Refresh active episode each turn (may change due to fork promotion).
        self._active_episode = self._episode_manager.ensure_active_episode(self.braid_id)
        # Append user message delta
        user_delta = self.store.append_message_delta("user", user_message, ProvenanceKind.user)
        start_delta_id = user_delta.id

        knot_id = str(uuid4())
        # Run cognition (two-pass: think -> microagent tools -> speak)
        req = KnotRequest(
            braid_id=self.braid_id,
            primary_episode_id=self._active_episode.id,
            user_message=user_message,
            max_recent_messages=settings.MAX_RECENT_MESSAGES,
        )
        try:
            think_res = self.knot_processor.think(req)
        except Exception as exc:
            # Record an observation delta so failures are visible in the braid.
            self.store.append_delta(
                GenericDelta(
                    id=str(uuid4()),
                    braid_id=self.braid_id,
                    kind=DeltaKind.observation,
                    provenance=Provenance(kind=ProvenanceKind.system),
                    confidence=0.3,
                    payload={"error": {"message": str(exc), "where": "knot_processor.think"}},
                )
            )
            raise

        planned_tools: list[dict[str, Any]] = []
        executed_tools: list[dict[str, Any]] = []
        mr = dict((think_res.thought_structured or {}).get("microagent_request") or {})
        if mr.get("should_spawn"):
            goal = str(mr.get("goal") or user_message)
            requested = [str(x) for x in (mr.get("requested_tools") or [])]
            allowed = [t for t in requested if t in self._tool_bead_refs]
            # Dedicated overlay episode for tools/microagents (do not change active episode).
            tool_episode_id = f"episode:tools:{self.braid_id}"
            tool_ep = self.store.get_episode(tool_episode_id)  # type: ignore[attr-defined]
            if tool_ep is None:
                from lmm.schema.episode import Episode

                tool_ep = Episode(
                    id=tool_episode_id,
                    braid_id=self.braid_id,
                    labels={"topics": ["tools"], "intents": ["act"], "modalities": ["text"]},
                    summary_cache={"created_ts": datetime.now(timezone.utc).isoformat()},
                )
                self.store.upsert_episode(tool_ep)  # type: ignore[attr-defined]

            ma = self._microagent_runner.run(
                braid_id=self.braid_id,
                knot_id=knot_id,
                episode_id=tool_ep.id,
                goal=goal,
                allowed_tools=allowed,
                tool_bead_refs={k: v for k, v in self._tool_bead_refs.items() if k in allowed},
                ribbon=think_res.ribbon,
            )
            planned_tools = ma.planned_tool_calls
            executed_tools = ma.executed_tools

        response_text = self.knot_processor.speak(req, ribbon_json=think_res.ribbon_json, executed_tools=executed_tools)
        tests = self.knot_processor._run_tests(  # type: ignore[attr-defined]
            req=req,
            ribbon=think_res.ribbon,
            planned_tools=planned_tools,
            executed_tools=executed_tools,
            response_text=response_text,
        )
        thought_structured = dict(think_res.thought_structured or {})
        thought_structured["tests"] = tests
        thought_structured["tool_stats"] = {"planned": len(planned_tools), "executed": len(executed_tools)}

        result = KnotResult(
            response_text=response_text,
            thought_narrative=think_res.thought_narrative,
            thought_structured=thought_structured,
            planned_tools=planned_tools,
            executed_tools=executed_tools,
            start_ts=think_res.start_ts,
            end_ts=datetime.now(timezone.utc).isoformat(),
        )

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
            knot_id=knot_id,
            primary_episode_id=self._active_episode.id,
            start_delta_id=start_delta_id,
            end_delta_id=end_delta_id,
            start_ts=result.start_ts,
            end_ts=result.end_ts,
            summary="Responded to user message (v2 skeleton).",
            thought_summary_bead_ref=thought_ref,
            planned_tools=result.planned_tools,
            executed_tools=result.executed_tools,
        )

        # Phase 2 (v0): write a semantic memory bead summarizing the turn
        semantic_write = self._semantic_consolidator.propose_turn_summary(
            user_text=user_message,
            assistant_text=result.response_text,
            evidence_delta_ids=[start_delta_id, end_delta_id],
            knot_id=knot.id,
        )
        # Phase 4 (v0): attach trust snapshot to derived semantic bead.
        try:
            tests = []
            if isinstance(result.thought_structured, dict):
                tests = list(result.thought_structured.get("tests") or [])
            engine = TrustEngine(
                promote_threshold=settings.TRUST_PROMOTE_THRESHOLD,
                half_life_seconds=settings.TRUST_DECAY_HALF_LIFE_SECONDS,
                provenance_weights_json=settings.TRUST_PROVENANCE_WEIGHTS_JSON,
            )
            evidence = [user_delta, assistant_delta]
            trust = engine.score_for_bead(
                evidence_deltas=evidence,
                tests=tests,
                provenance_kind=ProvenanceKind.system,
            )
            semantic_write.data["trust"] = {
                "score": trust.score,
                "decayed_score": trust.decayed_score,
                "state": trust.state,
                "created_ts": trust.details.get("created_ts"),
                "details": trust.details,
            }
        except Exception:
            pass
        semantic_ref = self.store.upsert_bead_version(
            bead_id=semantic_write.bead_id, bead_type=BeadType.memory_bead, data=semantic_write.data
        )
        # Qdrant indexing: upsert semantic bead into per-braid semantic collection.
        if self._semantic_index is not None:
            try:
                self._semantic_index.upsert_semantic_bead(
                    bead_version_id=str(semantic_ref.bead_version_id or ""),
                    user_text=str(semantic_write.data.get("user_text") or ""),
                    assistant_text=str(semantic_write.data.get("assistant_text") or ""),
                    payload={
                        "kind": str(semantic_write.data.get("kind") or ""),
                        "knot_id": str(semantic_write.data.get("knot_id") or ""),
                        "trust": dict(semantic_write.data.get("trust") or {}),
                    },
                )
            except Exception:
                pass
        self.store.append_delta(
            GenericDelta(
                id=str(uuid4()),
                braid_id=self.braid_id,
                kind=DeltaKind.bead_write,
                provenance=Provenance(kind=ProvenanceKind.system),
                confidence=0.55,
                payload={"bead_ref": semantic_ref.model_dump(), "kind": "semantic_turn_summary"},
            )
        )
        # Record a trust delta referencing the semantic bead.
        try:
            trust_payload = dict(semantic_write.data.get("trust") or {})
            self.store.append_delta(
                GenericDelta(
                    id=str(uuid4()),
                    braid_id=self.braid_id,
                    kind=DeltaKind.trust,
                    provenance=Provenance(kind=ProvenanceKind.system, episode_id=self._active_episode.id, knot_id=knot.id),
                    confidence=float(trust_payload.get("score") or 0.5),
                    payload={
                        "bead_ref": semantic_ref.model_dump(),
                        "trust": trust_payload,
                        "evidence_delta_ids": [start_delta_id, end_delta_id],
                    },
                )
            )
        except Exception:
            pass

        # Phase 3 (v0): fork proposal handling (pending-first) if enabled
        fork_event: dict[str, Any] = {}
        if settings.ENABLE_FORKING:
            tuned = self._get_metacog_fork_params()
            ttl_knots = int(tuned.get("pending_ttl_knots") or settings.FORK_PENDING_TTL_KNOTS)
            confirmation_required = int(tuned.get("confirmation_required") or settings.FORK_CONFIRMATION_REQUIRED)

            # Tick and enforce TTL for existing pending forks (best-effort).
            try:
                from lmm.schema.episode import EpisodeState

                now = datetime.now(timezone.utc).isoformat()
                pending_eps = self.store.list_episodes(state=EpisodeState.fork_pending, limit=50)
                for ep in pending_eps:
                    tick = self._episode_manager.tick_fork_pending(ep.id, now_ts=now)
                    # TTL by knot-count
                    pending_knot_count = int(tick.get("pending_knot_count") or 0)
                    # TTL by time (best-effort)
                    created_ts = (ep.summary_cache or {}).get("created_ts")
                    expired_by_time = False
                    if isinstance(created_ts, str) and created_ts:
                        try:
                            created = datetime.fromisoformat(created_ts.replace("Z", "+00:00"))
                            age_s = (datetime.now(timezone.utc) - created).total_seconds()
                            expired_by_time = age_s >= float(settings.FORK_PENDING_TTL_SECONDS)
                        except Exception:
                            expired_by_time = False

                    if pending_knot_count >= ttl_knots or expired_by_time:
                        self._episode_manager.expire_episode(ep.id)
            except Exception:
                pass

            fp = ((result.thought_structured or {}).get("fork") or {}) if isinstance(result.thought_structured, dict) else {}
            proposal = ForkProposal(
                should_fork=bool(fp.get("should_fork")),
                confidence=float(fp.get("confidence") or 0.0),
                reason=str(fp.get("reason") or ""),
                candidate_labels=dict(fp.get("candidate_episode_labels") or {"topics": [], "intents": [], "modalities": []}),
            )
            if proposal.should_fork and proposal.confidence >= 0.65:
                parent_episode_id = self._active_episode.id
                pending = self._episode_manager.propose_fork_pending(parent=self._active_episode, proposal=proposal)
                if pending is not None:
                    # Promote once it has enough confirmations
                    cc = int((pending.summary_cache or {}).get("confirmation_count") or 0)
                    if cc >= confirmation_required:
                        # Capture continuity buffer at promotion time
                        continuity = self.knot_processor._ribbon_provider.build_ribbon(
                            max_messages=settings.MAX_RECENT_MESSAGES
                        )
                        self._episode_manager.attach_continuity_snapshot(pending.id, continuity)

                        promoted = self._episode_manager.promote_fork(pending.id)
                        if promoted is not None:
                            self._active_episode = promoted
                    self.store.append_delta(
                        GenericDelta(
                            id=str(uuid4()),
                            braid_id=self.braid_id,
                            kind=DeltaKind.hypothesis,
                            provenance=Provenance(kind=ProvenanceKind.system, episode_id=pending.id),
                            confidence=min(0.9, max(0.1, proposal.confidence)),
                            payload={
                                "kind": "fork_pending",
                                "parent_episode_id": parent_episode_id,
                                "pending_episode_id": pending.id,
                                "labels": pending.labels,
                                "reason": proposal.reason,
                            },
                        )
                    )
                    fork_event = {"pending_episode_id": pending.id, "labels": pending.labels, "confidence": proposal.confidence}

        recent_deltas = self.store.get_recent_deltas(settings.TRACE_MAX_DELTAS)
        pending_eps = []
        if settings.ENABLE_FORKING:
            try:
                # best-effort: show fork-pending episodes
                from lmm.schema.episode import EpisodeState

                pending_eps = [e.model_dump() for e in self.store.list_episodes(state=EpisodeState.fork_pending, limit=10)]
            except Exception:
                pending_eps = []
        trace = {
            "braid_id": self.braid_id,
            "primary_episode_id": self._active_episode.id,
            "episode": self._active_episode.model_dump(),
            "fork": fork_event,
            "fork_pending": pending_eps,
            "knot": knot.model_dump(mode="json"),
            "deltas": [d.model_dump(mode="json") for d in recent_deltas],
        }

        return BraidTurnResult(
            response_text=result.response_text,
            thought_narrative=result.thought_narrative,
            trace=trace,
        )


