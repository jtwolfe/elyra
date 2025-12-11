from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Central configuration for the Elyra backend.

    Values are loaded from environment variables where possible so that
    different deployments (dev, staging, prod) can override defaults
    without code changes.
    """

    # LLM / Ollama
    OLLAMA_BASE_URL: AnyHttpUrl = "https://ollama.enphi.net:443"
    # Default model used by Elyra. Can be overridden via ELYRA_OLLAMA_MODEL.
    # Qwen 3 8B has strong tool-use capabilities and a 40k context window.
    OLLAMA_MODEL: str = "qwen3:8b"
    # HTTP timeout in seconds for requests to Ollama. On CPU-only setups with
    # larger models, this may need to be increased. Default is 5 minutes to
    # accommodate slower, long-running tool-using queries.
    OLLAMA_TIMEOUT_SECONDS: float = 600.0
    # Optional context window override for Ollama (num_ctx). The actual maximum
    # is constrained by the model; values above the model's limit are ignored
    # by Ollama. For Qwen 3 8B with a 40k window, 20000 uses ~50% of it.
    OLLAMA_NUM_CTX: int = 20000

    # Memory backends (used in later phases; stubs in Phase 1)
    REDIS_URL: str = "redis://localhost:6379/0"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    QDRANT_URL: AnyHttpUrl = "http://localhost:6333"

    # Feature flags
    ENABLE_REPLAY: bool = False
    ENABLE_DAEMON: bool = False
    # Enable simple JSON-backed episodic persistence in the HippocampalSim stub.
    # When disabled (default), HippocampalSim behaves as a pure in-memory stub,
    # which keeps tests and early experiments simple and fast. For local
    # development you can enable this via ELYRA_ENABLE_PERSISTENT_EPISODES=1
    # to keep a tiny JSON episodic log across restarts.
    ENABLE_PERSISTENT_EPISODES: bool = False

    # ChromaDB and embeddings
    CHROMA_DB_PATH: str = "data/chroma_db"
    DOCS_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Researcher settings
    RESEARCHER_MAX_ITERATIONS: int = 3
    RESEARCHER_MIN_RESULTS_THRESHOLD: int = 1

    class Config:
        env_prefix = "ELYRA_"
        case_sensitive = False


settings = Settings()


