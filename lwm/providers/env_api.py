"""Environment-configured API LLM provider (stub).

This module is intentionally non-functional out of the box. It expects
``LWM_API_KEY`` and ``LWM_API_ENDPOINT`` (and optionally ``LWM_API_MODEL``)
in the environment. Because default privacy policy forbids external API
calls, instantiating this provider only does so when the user opts in
via ``--llm api`` or ``LLM_PROVIDER=api``.

When invoked, it raises :class:`NotImplementedError` until a real
integration PR lands. This keeps the surface area honest: presence of
the provider is documented, but the privacy posture stays intact.
"""

from __future__ import annotations

import os

from lwm.providers import CompletionResult


class EnvApiProvider:
    name = "env_api"

    def __init__(self) -> None:
        if not os.environ.get("LWM_API_KEY") or not os.environ.get("LWM_API_ENDPOINT"):
            raise RuntimeError(
                "EnvApiProvider requires LWM_API_KEY and LWM_API_ENDPOINT. "
                "Use the default `noop` provider unless you have intentionally "
                "configured an external endpoint."
            )

    def complete(self, prompt: str, *, max_tokens: int = 512) -> CompletionResult:
        raise NotImplementedError(
            "EnvApiProvider.complete is not implemented in this build. "
            "Wire it to your provider's chat completion API in a follow-up."
        )

    def classify(self, text: str, labels: list[str]) -> tuple[str, float]:
        raise NotImplementedError(
            "EnvApiProvider.classify is not implemented in this build."
        )

    def is_noop(self) -> bool:
        return False


__all__ = ["EnvApiProvider"]
