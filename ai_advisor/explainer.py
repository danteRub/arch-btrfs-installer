from __future__ import annotations

from .models import CommandRisk, InstallPlan


_RISK_LABELS = {
    CommandRisk.SAFE: "read-only",
    CommandRisk.MEDIUM: "moderate change",
    CommandRisk.HIGH: "installation state change",
    CommandRisk.CRITICAL: "destructive or boot-critical operation",
}


def explain_plan(plan: InstallPlan) -> str:
    """Create a human-readable explanation for an InstallPlan.

    This module is intentionally deterministic. Future LLM explainers may be
    added behind this boundary, but they must not change risk labels, warnings,
    commands or confirmation requirements.
    """

    critical_commands = []
    high_commands = []
    safe_commands = []

    for step in plan.steps:
        if step.command is None:
            continue
        if step.command.risk == CommandRisk.CRITICAL:
            critical_commands.append(step.command.command)
        elif step.command.risk == CommandRisk.HIGH:
            high_commands.append(step.command.command)
        elif step.command.risk == CommandRisk.SAFE:
            safe_commands.append(step.command.command)

    lines: list[str] = []
    lines.append("# Plan explanation")
    lines.append("")
    lines.append("## What this plan does")
    lines.append(plan.summary)
    lines.append("")

    if plan.warnings:
        lines.append("## Warnings that require attention")
        for warning in plan.warnings:
            lines.append(f"- {warning}")
        lines.append("")

    lines.append("## Risk overview")
    lines.append(f"- Safe commands: {len(safe_commands)}")
    lines.append(f"- High-risk commands: {len(high_commands)}")
    lines.append(f"- Critical commands: {len(critical_commands)}")
    lines.append("")

    if critical_commands:
        lines.append("## Critical commands")
        lines.append(
            "These commands may destroy data, modify partitions, format filesystems "
            "or alter boot records. Review them manually before execution."
        )
        for command in critical_commands:
            lines.append(f"- `{command}`")
        lines.append("")

    if high_commands:
        lines.append("## High-risk commands")
        lines.append(
            "These commands change installation state, mount filesystems, install packages "
            "or modify the target system."
        )
        for command in high_commands:
            lines.append(f"- `{command}`")
        lines.append("")

    lines.append("## Human review checklist")
    lines.append("- Confirm the target disk manually with `lsblk`.")
    lines.append("- Confirm whether an EFI partition should be reused or created.")
    lines.append("- Confirm that Windows/NTFS partitions are not being overwritten unintentionally.")
    lines.append("- Confirm that network connectivity works before running `pacstrap`.")
    lines.append("- Do not execute critical commands from automation without explicit approval.")
    lines.append("")

    lines.append("## Safety boundary")
    lines.append(
        "This explanation does not execute commands and does not override deterministic "
        "risk classification."
    )

    return "\n".join(lines).rstrip() + "\n"


def explain_command_risk(risk: CommandRisk) -> str:
    """Return a stable explanation for a command risk label."""

    return _RISK_LABELS[risk]
