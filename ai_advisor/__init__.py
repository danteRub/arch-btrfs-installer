"""Safety-aware advisor components for Arch Btrfs installation planning."""

from .explainer import explain_command_risk, explain_plan
from .hardware_parser import DiskCandidate, HardwareSummary, summarize_hardware
from .llm_explainer import (
    LLMExplanationResult,
    build_llm_explanation_prompt,
    explain_plan_with_optional_llm,
    validate_llm_explanation,
)
from .models import CommandRisk, InstallCommand, InstallPlan, PlanStatus, SystemReport
from .openai_compatible import OpenAICompatibleClient, OpenAICompatibleClientError
from .planner import create_initial_plan
from .risk_classifier import classify_command

__all__ = [
    "CommandRisk",
    "DiskCandidate",
    "HardwareSummary",
    "InstallCommand",
    "InstallPlan",
    "LLMExplanationResult",
    "OpenAICompatibleClient",
    "OpenAICompatibleClientError",
    "PlanStatus",
    "SystemReport",
    "build_llm_explanation_prompt",
    "classify_command",
    "create_initial_plan",
    "explain_command_risk",
    "explain_plan",
    "explain_plan_with_optional_llm",
    "summarize_hardware",
    "validate_llm_explanation",
]
