from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .explainer import explain_plan
from .models import CommandRisk, InstallPlan


SYSTEM_PROMPT = """You are a safety-focused Linux installation advisor.

You may explain the provided installation plan, warnings and risks in clearer language.

You must not:
- execute commands,
- add new commands,
- remove commands,
- modify risk labels,
- downgrade critical or high-risk operations,
- hide warnings,
- invent hardware details,
- assume a disk is safe to erase,
- provide unattended destructive execution instructions.

If the plan contains critical commands, explicitly say that human confirmation is required.
"""


class LLMClient(Protocol):
    """Minimal protocol for injectable LLM clients.

    Production integrations can adapt OpenAI, Anthropic or local models to this
    protocol. Tests should use fake clients and must not require network access.
    """

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        """Return a completion for the supplied prompts."""


@dataclass(frozen=True)
class LLMExplanationResult:
    """Result returned by the optional LLM explanation layer."""

    explanation: str
    deterministic_fallback: str
    used_llm: bool


def build_llm_explanation_prompt(plan: InstallPlan) -> str:
    """Build a constrained prompt from a deterministic InstallPlan.

    The prompt serializes the plan as JSON so the model explains existing facts
    instead of inventing new installer state.
    """

    return (
        "Explain this Arch Linux installation plan for a human reviewer.\n\n"
        "Rules:\n"
        "- Do not add commands.\n"
        "- Do not remove warnings.\n"
        "- Do not change risk labels.\n"
        "- Keep critical commands clearly marked as requiring human confirmation.\n"
        "- Mention that the explanation is advisory only.\n\n"
        "InstallPlan JSON:\n"
        f"{plan.model_dump_json(indent=2)}\n"
    )


def validate_llm_explanation(plan: InstallPlan, explanation: str) -> list[str]:
    """Validate that an LLM explanation preserves critical safety signals.

    This is a defensive check. It does not prove the explanation is perfect, but
    it blocks obvious unsafe summaries that omit warnings or critical commands.
    """

    errors: list[str] = []
    normalized = explanation.lower()

    for warning in plan.warnings:
        first_words = " ".join(warning.split()[:3]).lower()
        if first_words and first_words not in normalized:
            errors.append(f"Missing warning signal: {first_words}")

    critical_commands = [
        step.command.command
        for step in plan.steps
        if step.command is not None and step.command.risk == CommandRisk.CRITICAL
    ]

    for command in critical_commands:
        if command.lower() not in normalized:
            errors.append(f"Missing critical command: {command}")

    if critical_commands and "human" not in normalized and "confirmation" not in normalized:
        errors.append("Critical commands require explicit human confirmation language.")

    return errors


def explain_plan_with_optional_llm(
    plan: InstallPlan,
    client: LLMClient | None = None,
) -> LLMExplanationResult:
    """Explain a plan with an optional LLM, falling back to deterministic output.

    The LLM is never required. If no client is provided, or if the LLM response
    fails validation, the deterministic explanation is returned.
    """

    fallback = explain_plan(plan)

    if client is None:
        return LLMExplanationResult(
            explanation=fallback,
            deterministic_fallback=fallback,
            used_llm=False,
        )

    prompt = build_llm_explanation_prompt(plan)
    candidate = client.complete(system_prompt=SYSTEM_PROMPT, user_prompt=prompt)
    errors = validate_llm_explanation(plan, candidate)

    if errors:
        return LLMExplanationResult(
            explanation=fallback,
            deterministic_fallback=fallback,
            used_llm=False,
        )

    return LLMExplanationResult(
        explanation=candidate.rstrip() + "\n",
        deterministic_fallback=fallback,
        used_llm=True,
    )
