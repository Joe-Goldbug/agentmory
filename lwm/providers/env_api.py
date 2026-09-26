"""Environment-configured OpenAI-compatible LLM provider.

The provider is opt-in and deliberately small. It supports local compatible
servers and remote endpoints without importing a vendor SDK or storing any
credential outside process memory. Memory policy, caching, and candidate
validation remain in :mod:`lwm.memory_compiler`.
"""

from __future__ import annotations

import json
import os
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from lwm.providers import CompletionResult


DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RESPONSE_BYTES = 256 * 1024
DEFAULT_MAX_TOKENS = 4096
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0"})


def _int_env(env: Mapping[str, str], key: str, default: int) -> int:
    raw = str(env.get(key, default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{key} must be an integer") from exc
    if value <= 0:
        raise RuntimeError(f"{key} must be greater than zero")
    return value


class EnvApiProvider:
    """Call a configured ``/chat/completions`` compatible endpoint."""

    name = "env_api"

    def __init__(self, *, env: Mapping[str, str] | None = None) -> None:
        values = os.environ if env is None else env
        self.endpoint = str(values.get("LWM_API_ENDPOINT", "")).strip()
        self.api_key = str(values.get("LWM_API_KEY", "")).strip()
        self.model = str(values.get("LWM_API_MODEL", "default")).strip() or "default"
        self.timeout_seconds = _int_env(
            values, "LWM_API_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS
        )
        self.max_response_bytes = _int_env(
            values, "LWM_API_MAX_RESPONSE_BYTES", DEFAULT_MAX_RESPONSE_BYTES
        )

        parsed = urlparse(self.endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError(
                "EnvApiProvider requires LWM_API_ENDPOINT as an http(s) URL"
            )
        if parsed.hostname not in LOCAL_HOSTS and not self.api_key:
            raise RuntimeError(
                "EnvApiProvider requires LWM_API_KEY for a non-local endpoint"
            )

    def _completion_url(self) -> str:
        suffix = "/chat/completions"
        endpoint = self.endpoint.rstrip("/")
        return endpoint if endpoint.endswith(suffix) else endpoint + suffix

    def _request(self, messages: list[dict[str, str]], *, max_tokens: int) -> dict[str, Any]:
        bounded_tokens = max(1, min(int(max_tokens), DEFAULT_MAX_TOKENS))
        body = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": bounded_tokens,
            "messages": messages,
        }
        request = Request(
            self._completion_url(),
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read(self.max_response_bytes + 1)
        except HTTPError as exc:
            raise RuntimeError(f"EnvApiProvider request failed: HTTP {exc.code}") from None
        except (TimeoutError, URLError, OSError) as exc:
            raise RuntimeError(
                f"EnvApiProvider request failed: {type(exc).__name__}"
            ) from None

        if len(raw) > self.max_response_bytes:
            raise RuntimeError("EnvApiProvider response exceeded the configured byte limit")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise RuntimeError("EnvApiProvider returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("EnvApiProvider returned a non-object JSON payload")
        return payload

    @staticmethod
    def _content(payload: Mapping[str, Any]) -> str:
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("EnvApiProvider response misses message content") from exc
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("EnvApiProvider message content must be non-empty text")
        return content

    def complete(self, prompt: str, *, max_tokens: int = 512) -> CompletionResult:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be non-empty text")
        payload = self._request(
            [
                {
                    "role": "system",
                    "content": "Return only the requested answer. Do not invent evidence.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
        )
        return CompletionResult(text=self._content(payload))

    def classify(self, text: str, labels: list[str]) -> tuple[str, float]:
        clean_labels = [label.strip() for label in labels if isinstance(label, str) and label.strip()]
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be non-empty text")
        if not clean_labels:
            raise ValueError("labels must contain at least one non-empty label")
        result = self.complete(
            "Return JSON only in the form {\"label\": \"...\", \"confidence\": 0}. "
            f"The label must be one of {json.dumps(clean_labels, ensure_ascii=False)}.\n"
            f"Text:\n{text}",
            max_tokens=128,
        )
        try:
            payload = json.loads(result.text)
        except ValueError as exc:
            raise RuntimeError("EnvApiProvider classifier returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("EnvApiProvider classifier returned a non-object")
        label = payload.get("label")
        confidence = payload.get("confidence")
        if label not in clean_labels or not isinstance(confidence, (int, float)):
            raise RuntimeError("EnvApiProvider classifier returned an invalid result")
        return str(label), max(0.0, min(float(confidence), 1.0))

    def is_noop(self) -> bool:
        return False


__all__ = ["DEFAULT_MAX_RESPONSE_BYTES", "EnvApiProvider"]
