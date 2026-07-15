"""Registry backend for in-process LLM provider factories.

Keeps registration out of :mod:`lwm.providers.__init__` so the public
module stays small. Tests use this to inject a fake provider.
"""

from __future__ import annotations

from typing import Any

_REGISTRY: dict[str, Any] = {}


def get(name: str) -> Any:
    return _REGISTRY.get(name.strip().lower())


def has(name: str) -> bool:
    return name.strip().lower() in _REGISTRY


def names() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))
