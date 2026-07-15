"""Deterministic no-op LLM provider.

The hub ships in deterministic mode by default; this provider returns
empty strings and zero confidence for every call. The ingest pipeline
gracefully falls back to rule-based logic when ``complete()`` returns
no result.
"""

from __future__ import annotations

from lwm.providers import CompletionResult


class NoopProvider:
    name = "noop"

    def complete(self, prompt: str, *, max_tokens: int = 512) -> CompletionResult:
        return CompletionResult(text="", confidence=0.0)

    def classify(self, text: str, labels: list[str]) -> tuple[str, float]:
        return ("", 0.0)

    def is_noop(self) -> bool:
        return True


__all__ = ["NoopProvider"]
