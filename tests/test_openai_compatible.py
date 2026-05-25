import json
import urllib.error

import pytest

from ai_advisor.openai_compatible import (
    OpenAICompatibleClient,
    OpenAICompatibleClientError,
    _extract_chat_completion_text,
)


def test_extract_chat_completion_text() -> None:
    payload = {"choices": [{"message": {"content": "hello"}}]}

    assert _extract_chat_completion_text(payload) == "hello"


def test_extract_chat_completion_text_rejects_malformed_payload() -> None:
    with pytest.raises(OpenAICompatibleClientError, match="Malformed"):
        _extract_chat_completion_text({"choices": []})


def test_from_env_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("AI_ADVISOR_OPENAI_API_KEY", raising=False)

    with pytest.raises(OpenAICompatibleClientError, match="AI_ADVISOR_OPENAI_API_KEY"):
        OpenAICompatibleClient.from_env()


def test_from_env_reads_configuration(monkeypatch) -> None:
    monkeypatch.setenv("AI_ADVISOR_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AI_ADVISOR_OPENAI_MODEL", "test-model")
    monkeypatch.setenv("AI_ADVISOR_OPENAI_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("AI_ADVISOR_OPENAI_TIMEOUT_SECONDS", "7")

    client = OpenAICompatibleClient.from_env()

    assert client.api_key == "test-key"
    assert client.model == "test-model"
    assert client.base_url == "http://localhost:1234/v1"
    assert client.timeout_seconds == 7


def test_complete_uses_chat_completions_payload(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "safe explanation"}}]}).encode(
                "utf-8"
            )

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = OpenAICompatibleClient(
        api_key="test-key",
        model="test-model",
        base_url="http://localhost:1234/v1",
        timeout_seconds=9,
    )

    result = client.complete(system_prompt="system", user_prompt="user")

    assert result == "safe explanation"
    assert captured["url"] == "http://localhost:1234/v1/chat/completions"
    assert captured["timeout"] == 9
    assert captured["body"]["model"] == "test-model"
    assert captured["body"]["messages"][0] == {"role": "system", "content": "system"}
    assert captured["body"]["messages"][1] == {"role": "user", "content": "user"}


def test_complete_wraps_url_errors(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = OpenAICompatibleClient(api_key="test-key")

    with pytest.raises(OpenAICompatibleClientError, match="request failed"):
        client.complete(system_prompt="system", user_prompt="user")
