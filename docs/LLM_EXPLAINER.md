# Optional LLM Explainer

The optional LLM explainer is a safety-bounded layer for improving human-readable explanations of deterministic installation plans.

It is not required for normal operation.

## Design goal

The deterministic pipeline remains authoritative:

```text
SystemReport -> HardwareSummary -> InstallPlan -> deterministic risk classifier
```

The LLM layer may only explain the already-generated plan.

## What the LLM may do

- Explain warnings in clearer language.
- Summarize critical and high-risk commands.
- Produce a human-friendly review checklist.
- Make the plan easier to understand.

## What the LLM must not do

- Execute commands.
- Add new commands.
- Remove commands.
- Change risk labels.
- Downgrade critical or high-risk operations.
- Hide warnings.
- Invent hardware details.
- Assume a disk is safe to erase.
- Provide unattended destructive execution instructions.

## Interface

Implement the `LLMClient` protocol:

```python
class LLMClient(Protocol):
    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        ...
```

Example adapter shape:

```python
from ai_advisor.llm_explainer import explain_plan_with_optional_llm

class MyLLMClient:
    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        # Call OpenAI, Anthropic, a local model, etc.
        # Return plain text.
        return "..."

result = explain_plan_with_optional_llm(plan, client=MyLLMClient())
print(result.explanation)
```

## OpenAI-compatible provider

The package includes a minimal OpenAI-compatible client using Python's standard library:

```python
from ai_advisor.openai_compatible import OpenAICompatibleClient

client = OpenAICompatibleClient.from_env()
result = explain_plan_with_optional_llm(plan, client=client)
```

Environment variables:

| Variable | Required | Default | Meaning |
| --- | --- | --- | --- |
| `AI_ADVISOR_OPENAI_API_KEY` | yes | none | API key or compatible bearer token. |
| `AI_ADVISOR_OPENAI_MODEL` | no | `gpt-4.1-mini` | Chat model name. |
| `AI_ADVISOR_OPENAI_BASE_URL` | no | `https://api.openai.com/v1` | OpenAI-compatible API base URL. |
| `AI_ADVISOR_OPENAI_TIMEOUT_SECONDS` | no | `30` | Request timeout in seconds. |

CLI usage:

```bash
AI_ADVISOR_OPENAI_API_KEY=... \
python -m ai_advisor diagnostics/system_report.json --explain --llm-provider openai-compatible
```

The provider is only available with `--explain`. It is not available with `--json` or raw plan mode.

## Fallback behavior

If no client is provided, the deterministic explanation is used.

If the LLM response fails safety validation, the deterministic explanation is used.

```python
result = explain_plan_with_optional_llm(plan)
assert result.used_llm is False
```

## Validation

The validator checks that obvious safety signals are preserved:

- warnings are still represented,
- critical commands are still mentioned,
- critical commands include human confirmation language.

This validation is defensive. It does not prove the LLM output is perfect. It only blocks unsafe or incomplete summaries from replacing the deterministic explanation.

## Testing rule

Tests must not require network access or real API keys. Use fake clients or monkeypatch network calls.
