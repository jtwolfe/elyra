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
    OLLAMA_BASE_URL: AnyHttpUrl = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral:7b-instruct-v0.3-q6_K"
    # HTTP timeout in seconds for requests to Ollama. On CPU-only setups with
    # larger models, this may need to be increased.
    OLLAMA_TIMEOUT_SECONDS: float = 180.0
    # Optional context window override for Ollama (num_ctx). The actual maximum
    # is constrained by the model; values above the model's limit are ignored
    # by Ollama. For Mistral models with a 32k window, 16384 uses ~50% of it.
    OLLAMA_NUM_CTX: int = 16384

    # Memory backends (used in later phases; stubs in Phase 1)
    REDIS_URL: str = "redis://localhost:6379/0"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    QDRANT_URL: AnyHttpUrl = "http://localhost:6333"

    # Feature flags
    ENABLE_REPLAY: bool = False
    ENABLE_DAEMON: bool = False

    class Config:
        env_prefix = "ELYRA_"
        case_sensitive = False


settings = Settings()


