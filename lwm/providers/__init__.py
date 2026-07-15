"""LLM provider abstraction.

The hub keeps LLM usage behind a tiny Protocol so the rest of the code
does not care whether the implementation is a no-op (default), Ollama,
or an HTTP API. Adding a new provider is a single new module that
implements :class:`LLMProvider`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class CompletionResult:
    text: str
    confidence: float = 0.0


class LLMProvider(Protocol):
    """Minimal interface the ingest pipeline depends on."""

    name: str

    def complete(self, prompt: str, *, max_tokens: int = 512) -> CompletionResult: ...

    def classify(self, text: str, labels: list[str]) -> tuple[str, float]: ...

    def is_noop(self) -> bool: ...


def get_provider(name: str | None = None) -> LLMProvider:
    """Resolve a provider by short name. Defaults to ``noop``."""

    chosen = (name or "").strip().lower() or "noop"
    if chosen == "noop":
        from lwm.providers.noop import NoopProvider

        return NoopProvider()
    if chosen in {"env", "api"}:
        from lwm.providers.env_api import EnvApiProvider

        return EnvApiProvider()
    raise ValueError(f"unknown LLM provider: {name!r}")


def register_provider(name: str, factory: Any) -> None:
    """Register an in-process provider factory. Use for tests."""

    # Local registry avoids pulling in extra deps just to register.
    from lwm.providers import registry as _registry

    _registry._REGISTRY[name.strip().lower()] = factory  # type: ignore[attr-defined]


__all__ = ["CompletionResult", "LLMProvider", "get_provider", "register_provider"]
