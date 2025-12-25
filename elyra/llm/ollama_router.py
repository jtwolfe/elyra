from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from elyra.runtime.settings import get_v2_settings


@dataclass(frozen=True)
class OllamaChatResult:
    content: str
    raw: dict[str, Any]


class OllamaRouterClient:
    """Small sync Ollama client with primary->fallback failover.

    Notes:
    - Uses `/api/chat` non-streaming.
    - Supports best-effort JSON-mode responses (via Ollama `format: "json"`).
    """

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        base_url_primary: Optional[str] = None,
        base_url_fallback: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        num_ctx: Optional[int] = None,
    ) -> None:
        s = get_v2_settings()
        self._model = model or s.OLLAMA_MODEL
        self._primary = base_url_primary or str(s.OLLAMA_BASE_URL_PRIMARY)
        self._fallback = base_url_fallback or str(s.OLLAMA_BASE_URL_FALLBACK)
        self._timeout = timeout_seconds or s.OLLAMA_TIMEOUT_SECONDS
        self._num_ctx = num_ctx or s.OLLAMA_NUM_CTX

    def chat_result(self, messages: list[dict[str, Any]], *, force_json: bool = False) -> OllamaChatResult:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {"num_ctx": self._num_ctx},
        }
        if force_json:
            payload["format"] = "json"

        last_exc: Optional[Exception] = None
        for base_url in (self._primary, self._fallback):
            try:
                with httpx.Client(base_url=base_url, timeout=self._timeout) as client:
                    resp = client.post("/api/chat", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    msg = (data or {}).get("message") or {}
                    content = msg.get("content")
                    if not isinstance(content, str):
                        raise RuntimeError("Unexpected response format from Ollama (/api/chat)")
                    return OllamaChatResult(content=content, raw=data)
            except (httpx.TimeoutException, httpx.HTTPError, ValueError, RuntimeError) as exc:
                last_exc = exc
                continue

        raise RuntimeError(
            f"All Ollama endpoints failed (primary={self._primary}, fallback={self._fallback})."
        ) from last_exc

    def chat(self, messages: list[dict[str, Any]]) -> str:
        """Chat returning only the assistant text content (Protocol-friendly)."""
        return self.chat_result(messages).content

    def chat_json(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Request a JSON object and parse it. Raises if parsing fails."""
        r = self.chat_result(messages, force_json=True)
        try:
            return json.loads(r.content)
        except json.JSONDecodeError as exc:
            # Some models may wrap JSON in prose; try to recover via a minimal extraction.
            start = r.content.find("{")
            end = r.content.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(r.content[start : end + 1])
                except Exception:
                    pass
            # Retry once with an explicit repair instruction.
            repair_messages = list(messages) + [
                {
                    "role": "system",
                    "content": (
                        "Your previous output was not valid JSON. "
                        "Return ONLY a valid JSON object matching the requested schema. "
                        "No prose, no markdown, no code fences."
                    ),
                }
            ]
            r2 = self.chat_result(repair_messages, force_json=True)
            try:
                return json.loads(r2.content)
            except Exception as exc2:
                raise RuntimeError("Ollama did not return valid JSON for chat_json().") from exc2


