"""Test the no-op LLM provider."""

from __future__ import annotations

from lwm.providers import get_provider
from lwm.providers.noop import NoopProvider


def test_default_provider_is_noop() -> None:
    provider = get_provider()
    assert isinstance(provider, NoopProvider)
    assert provider.is_noop()


def test_noop_complete_is_empty() -> None:
    provider = NoopProvider()
    result = provider.complete("anything", max_tokens=64)
    assert result.text == ""
    assert result.confidence == 0.0


def test_noop_classify_is_empty() -> None:
    provider = NoopProvider()
    label, confidence = provider.classify("text", labels=["a", "b"])
    assert label == ""
    assert confidence == 0.0


def test_unknown_provider_raises() -> None:
    import pytest

    with pytest.raises(ValueError):
        get_provider("nope-not-a-provider")


def test_env_api_provider_requires_env(monkeypatch) -> None:
    from lwm.providers.env_api import EnvApiProvider

    monkeypatch.delenv("LWM_API_KEY", raising=False)
    monkeypatch.delenv("LWM_API_ENDPOINT", raising=False)
    import pytest

    with pytest.raises(RuntimeError):
        EnvApiProvider()
