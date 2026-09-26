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


def test_env_api_provider_calls_local_openai_compatible_endpoint(monkeypatch) -> None:
    from lwm.providers import env_api
    from lwm.providers.env_api import EnvApiProvider

    captured: dict[str, object] = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit: int) -> bytes:
            return json.dumps(
                {"choices": [{"message": {"content": "bounded answer"}}]}
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return Response()

    import json

    monkeypatch.setattr(env_api, "urlopen", fake_urlopen)
    provider = EnvApiProvider(
        env={
            "LWM_API_ENDPOINT": "http://localhost:11434/v1",
            "LWM_API_MODEL": "qwen-local",
        }
    )
    result = provider.complete("use only this evidence", max_tokens=9000)

    assert result.text == "bounded answer"
    assert captured["url"] == "http://localhost:11434/v1/chat/completions"
    assert captured["timeout"] == 30
    assert captured["body"]["model"] == "qwen-local"
    assert captured["body"]["temperature"] == 0
    assert captured["body"]["max_tokens"] == 4096


def test_env_api_provider_classify_requires_valid_label(monkeypatch) -> None:
    from lwm.providers import env_api
    from lwm.providers.env_api import EnvApiProvider

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit: int) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {"message": {"content": '{"label":"workflow","confidence":1.4}'}},
                    ]
                }
            ).encode("utf-8")

    import json

    monkeypatch.setattr(env_api, "urlopen", lambda *_args, **_kwargs: Response())
    provider = EnvApiProvider(env={"LWM_API_ENDPOINT": "http://127.0.0.1:9000/v1"})

    assert provider.classify("evidence", ["workflow", "relationship"]) == ("workflow", 1.0)


def test_env_api_provider_rejects_remote_without_key() -> None:
    from lwm.providers.env_api import EnvApiProvider
    import pytest

    with pytest.raises(RuntimeError, match="non-local endpoint"):
        EnvApiProvider(env={"LWM_API_ENDPOINT": "https://example.test/v1"})


def test_env_api_provider_rejects_oversized_response(monkeypatch) -> None:
    from lwm.providers import env_api
    from lwm.providers.env_api import EnvApiProvider
    import pytest

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, limit: int) -> bytes:
            return b"x" * limit

    monkeypatch.setattr(env_api, "urlopen", lambda *_args, **_kwargs: Response())
    provider = EnvApiProvider(
        env={
            "LWM_API_ENDPOINT": "http://localhost:11434/v1",
            "LWM_API_MAX_RESPONSE_BYTES": "8",
        }
    )

    with pytest.raises(RuntimeError, match="byte limit"):
        provider.complete("x")
