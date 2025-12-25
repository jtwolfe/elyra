from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from lmm.schema.delta import GenericDelta, ProvenanceKind


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


@dataclass(frozen=True)
class TrustScore:
    score: float
    decayed_score: float
    state: str  # "probation" | "promoted" | "demoted"
    details: dict[str, Any]


class TrustEngine:
    """Phase 4 v0 trust engine.

    Goals for v0:
    - deterministic scoring
    - integrates test harness results + provenance weighting
    - supports read-time decay without mutating historical bead versions
    """

    def __init__(
        self,
        *,
        promote_threshold: float,
        half_life_seconds: int,
        provenance_weights_json: str,
    ) -> None:
        self._promote_threshold = float(promote_threshold)
        self._half_life_seconds = max(1, int(half_life_seconds))
        try:
            self._prov_w = dict(json.loads(provenance_weights_json or "{}"))
        except Exception:
            self._prov_w = {}

    def score_for_bead(
        self,
        *,
        evidence_deltas: list[GenericDelta],
        tests: list[dict[str, Any]],
        provenance_kind: ProvenanceKind,
        created_ts: str | None = None,
    ) -> TrustScore:
        evidence_conf = [float(d.confidence) for d in evidence_deltas] or [0.5]
        evidence_mean = sum(evidence_conf) / len(evidence_conf)

        test_scores = [float((t or {}).get("score") or 0.0) for t in (tests or []) if isinstance(t, dict)]
        tests_mean = (sum(test_scores) / len(test_scores)) if test_scores else 0.5
        any_failed = any((isinstance(t, dict) and not bool(t.get("passed", True))) for t in (tests or []))

        prov_weight = float(self._prov_w.get(str(provenance_kind.value), 0.85))

        raw = 0.5 * evidence_mean + 0.5 * tests_mean
        if any_failed:
            raw *= 0.5
        raw *= prov_weight
        raw = _clamp01(raw)

        ts = created_ts or _now_iso()
        decayed = self.decay_score(raw, created_ts=ts, now_ts=_now_iso())
        decayed = _clamp01(decayed)

        state = "promoted" if (raw >= self._promote_threshold and not any_failed) else "probation"
        return TrustScore(
            score=raw,
            decayed_score=decayed,
            state=state,
            details={
                "evidence_mean_confidence": evidence_mean,
                "tests_mean_score": tests_mean,
                "any_test_failed": any_failed,
                "provenance_weight": prov_weight,
                "promote_threshold": self._promote_threshold,
                "half_life_seconds": self._half_life_seconds,
                "created_ts": ts,
            },
        )

    def decay_score(self, score: float, *, created_ts: str, now_ts: str) -> float:
        try:
            created = _parse_iso(created_ts)
            now = _parse_iso(now_ts)
            age_s = max(0.0, (now - created).total_seconds())
        except Exception:
            age_s = 0.0
        # half-life decay: score * 0.5^(age/half_life)
        return float(score) * (0.5 ** (age_s / float(self._half_life_seconds)))


