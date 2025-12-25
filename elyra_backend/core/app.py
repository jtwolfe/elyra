"""Compatibility wrapper for the Elyra v2 FastAPI app.

Historically the repo exposed `elyra_backend.core.app:app` (Phase 1 MVP).
For the Braid v2 skeleton, the canonical app lives in `elyra.api.app`.
"""

from elyra.api.app import app

__all__ = ["app"]


