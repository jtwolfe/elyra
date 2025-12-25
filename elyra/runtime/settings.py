from __future__ import annotations

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings


class ElyraV2Settings(BaseSettings):
    """Configuration for Elyra v2 (Braid) composition layer.

    Environment variables:
    - ELYRA_LLM_BACKEND: \"ollama\" (default) or \"mock\"
    - ELYRA_OLLAMA_MODEL: model name (default: gpt-oss:latest)
    - ELYRA_OLLAMA_BASE_URL_PRIMARY: primary Ollama base URL
    - ELYRA_OLLAMA_BASE_URL_FALLBACK: fallback Ollama base URL
    - ELYRA_OLLAMA_TIMEOUT_SECONDS: request timeout (seconds)
    - ELYRA_OLLAMA_NUM_CTX: Ollama num_ctx hint
    """

    # LLM backend selection (offline tests can set this to "mock")
    LLM_BACKEND: str = "ollama"

    # Ollama routing
    OLLAMA_MODEL: str = "gpt-oss:latest"
    # IMPORTANT: do not hardcode private/shared endpoints in source control.
    # Configure these via env vars on your local system.
    OLLAMA_BASE_URL_PRIMARY: AnyHttpUrl = "http://localhost:11434"
    OLLAMA_BASE_URL_FALLBACK: AnyHttpUrl = "http://localhost:11434"
    OLLAMA_TIMEOUT_SECONDS: float = 600.0
    OLLAMA_NUM_CTX: int = 20000

    # Context/ribbon budgeting
    # How many recent message deltas to include in the continuity buffer.
    MAX_RECENT_MESSAGES: int = 20
    # How many deltas to include in trace payloads for the UI.
    TRACE_MAX_DELTAS: int = 50
    # How many recent deltas to load from the store when building a ribbon.
    RIBBON_MAX_DELTAS: int = 500
    # How many recent knots to load from the store when building a ribbon.
    RIBBON_MAX_KNOTS: int = 50
    # How many semantic bead versions to include in the ribbon.
    RIBBON_MAX_SEMANTIC_BEADS: int = 10

    # Persistence / external backends
    # Options: "memory" (default), "neo4j"
    PERSISTENCE_BACKEND: str = "memory"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    # Vector store (foundation; used more heavily in Phase 2+)
    QDRANT_URL: str = "http://localhost:6333"
    ENABLE_QDRANT: bool = False
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    QDRANT_TOP_K: int = 8

    # Forking (Phase 3)
    ENABLE_FORKING: bool = False
    FORK_PENDING_TTL_KNOTS: int = 8
    FORK_PENDING_TTL_SECONDS: int = 15 * 60
    FORK_CONFIRMATION_REQUIRED: int = 2

    # Trust (Phase 4)
    TRUST_PROMOTE_THRESHOLD: float = 0.75
    TRUST_DECAY_HALF_LIFE_SECONDS: int = 24 * 60 * 60
    # JSON so it's easy to override as a single env var.
    TRUST_PROVENANCE_WEIGHTS_JSON: str = (
        '{"user": 1.0, "assistant": 0.85, "tool": 0.95, "perception": 0.9, "system": 0.8, "dream": 0.6}'
    )

    # Tools
    ENABLE_WEB_SEARCH: bool = False

    # Background workers (Phase 5)
    ENABLE_BACKGROUND_WORKERS: bool = False
    DREAM_INTERVAL_SECONDS: int = 60
    METACOG_INTERVAL_SECONDS: int = 120
    METACOG_WINDOW_TURNS: int = 25

    # Dangerous admin endpoints (dev only)
    ENABLE_DANGEROUS_ADMIN: bool = False

    class Config:
        env_prefix = "ELYRA_"
        case_sensitive = False


def get_v2_settings() -> ElyraV2Settings:
    """Load settings from the current environment.

    We intentionally construct settings at call-time so tests can switch
    between offline/mock and live backends without relying on import order.
    """

    return ElyraV2Settings()


v2_settings = get_v2_settings()


