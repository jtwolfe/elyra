from typing import Any, Dict, List, Optional

import httpx

from elyra_backend.config import settings


class OllamaClient:
    """
    Minimal async client for talking to an Ollama server.

    This wrapper is intentionally small and opinionated for the Phase 1 MVP.
    It assumes the standard `/api/chat` Ollama endpoint and returns the
    assistant's message content as a plain string.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        num_ctx: Optional[int] = None,
    ) -> None:
        self._base_url = base_url or str(settings.OLLAMA_BASE_URL)
        self._model = model or settings.OLLAMA_MODEL
        # If no timeout is provided, fall back to the configured default.
        self._timeout = timeout or settings.OLLAMA_TIMEOUT_SECONDS
        # Optional context window hint; actual maximum is enforced by the model.
        self._num_ctx = num_ctx or settings.OLLAMA_NUM_CTX

    async def chat(self, messages: List[Dict[str, Any]]) -> str:
        """
        Send a non-streaming chat request to Ollama and return the text content.

        Parameters
        ----------
        messages:
            List of role/content dicts, e.g.:
            [{"role": "system", "content": "You are Elyra..."}, ...]
        
        Raises
        ------
        httpx.HTTPStatusError:
            If the server returns an error status (e.g., 504 Gateway Timeout)
        httpx.TimeoutException:
            If the request times out
        """
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=self._timeout
            ) as client:
                response = await client.post(
                    "/api/chat",
                    json={
                        "model": self._model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            # Use a conservative fraction of the model's context
                            # window. Ollama will clamp this to the model's limit
                            # if it is too large.
                            "num_ctx": self._num_ctx,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                # Ollama's /api/chat returns a single message in 'message'.
                message = data.get("message") or {}
                content = message.get("content")
                if not isinstance(content, str):
                    raise RuntimeError("Unexpected response format from Ollama")
                return content
        except httpx.HTTPStatusError as exc:
            # Re-raise with more context for 5xx errors
            if exc.response.status_code >= 500:
                raise RuntimeError(
                    f"Ollama server error ({exc.response.status_code}): "
                    f"The LLM server is experiencing issues. Please try again in a moment."
                ) from exc
            raise
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                f"Request to Ollama server timed out after {self._timeout}s. "
                f"The server may be overloaded. Please try again."
            ) from exc


