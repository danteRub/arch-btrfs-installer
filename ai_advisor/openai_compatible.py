from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .llm_explainer import LLMClient


DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4.1-mini"


class OpenAICompatibleClientError(RuntimeError):
    """Raised when an OpenAI-compatible request fails."""


@dataclass(frozen=True)
class OpenAICompatibleClient(LLMClient):
    """Minimal OpenAI-compatible chat completions client.

    This client intentionally uses only Python's standard library so the core
    package does not depend on a specific provider SDK.

    It can be used with OpenAI-compatible endpoints such as OpenAI, LiteLLM,
    vLLM gateways or compatible local proxies.
    """

    api_key: str
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: int = 30

    @classmethod
    def from_env(cls) -> "OpenAICompatibleClient":
        """Create a client from environment variables.

        Required:
        - `AI_ADVISOR_OPENAI_API_KEY`

        Optional:
        - `AI_ADVISOR_OPENAI_MODEL`
        - `AI_ADVISOR_OPENAI_BASE_URL`
        - `AI_ADVISOR_OPENAI_TIMEOUT_SECONDS`
        """

        api_key = os.getenv("AI_ADVISOR_OPENAI_API_KEY")
        if not api_key:
            raise OpenAICompatibleClientError(
                "AI_ADVISOR_OPENAI_API_KEY is required for OpenAI-compatible explanations."
            )

        timeout_raw = os.getenv("AI_ADVISOR_OPENAI_TIMEOUT_SECONDS", "30")
        try:
            timeout_seconds = int(timeout_raw)
        except ValueError as exc:
            raise OpenAICompatibleClientError(
                "AI_ADVISOR_OPENAI_TIMEOUT_SECONDS must be an integer."
            ) from exc

        return cls(
            api_key=api_key,
            model=os.getenv("AI_ADVISOR_OPENAI_MODEL", DEFAULT_MODEL),
            base_url=os.getenv("AI_ADVISOR_OPENAI_BASE_URL", DEFAULT_BASE_URL),
            timeout_seconds=timeout_seconds,
        )

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        endpoint = self.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise OpenAICompatibleClientError(
                f"OpenAI-compatible endpoint returned HTTP {exc.code}: {error_body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise OpenAICompatibleClientError(
                f"OpenAI-compatible endpoint request failed: {exc.reason}"
            ) from exc

        return _extract_chat_completion_text(json.loads(body))


def _extract_chat_completion_text(payload: dict[str, Any]) -> str:
    """Extract assistant text from an OpenAI-compatible chat completion payload."""

    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OpenAICompatibleClientError("Malformed chat completion response.") from exc

    if not isinstance(content, str) or not content.strip():
        raise OpenAICompatibleClientError("Chat completion response did not contain text.")

    return content
