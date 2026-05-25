from __future__ import annotations

from .hardware_parser import HardwareSummary
from .models import CommandRisk, InstallPlan, PlanStatus


_STATUS_RECOMMENDATION = {
    PlanStatus.READY: "Plan appears ready for human review. No blocking conditions were detected.",
    PlanStatus.NEEDS_REVIEW: "Manual review is required before executing installation steps.",
    PlanStatus.BLOCKED: "Planning is blocked. Resolve the blocking conditions before continuing.",
}


def render_doctor_report(summary: HardwareSummary, plan: InstallPlan) -> str:
    """Render a concise advisor health report.

    The doctor report is read-only. It summarizes already-computed diagnostic and
    planning signals; it does not execute commands or alter risk labels.
    """

    critical_count = _count_commands(plan, CommandRisk.CRITICAL)
    high_count = _count_commands(plan, CommandRisk.HIGH)
    safe_count = _count_commands(plan, CommandRisk.SAFE)
    efi_detected = any(disk.has_efi_partition for disk in summary.disks)
    windows_detected = summary.possible_windows_dual_boot or any(
        disk.has_windows_markers for disk in summary.disks
    )

    lines: list[str] = []
    lines.append("# Advisor doctor report")
    lines.append("")
    lines.append("## Overall")
    lines.append(f"- Status: `{plan.status.value}`")
    lines.append(f"- Recommendation: {_STATUS_RECOMMENDATION[plan.status]}")
    lines.append("")

    if plan.status_reasons:
        lines.append("## Status reasons")
        for reason in plan.status_reasons:
            lines.append(f"- {reason}")
        lines.append("")

    lines.append("## System signals")
    lines.append(f"- Boot mode: `{summary.boot_mode}`")
    lines.append(f"- CPU vendor: `{summary.cpu_vendor}`")
    lines.append(f"- Microcode package: `{summary.microcode_package or 'unknown'}`")
    lines.append(f"- Network link detected: `{_format_bool(summary.network_link_up)}`")
    lines.append(f"- Disk candidates: `{len(summary.disks)}`")
    lines.append(f"- EFI partition detected: `{_format_bool(efi_detected)}`")
    lines.append(f"- Windows/NTFS markers detected: `{_format_bool(windows_detected)}`")
    lines.append("")

    if summary.disks:
        lines.append("## Disk candidates")
        for disk in summary.disks:
            lines.append(
                "- "
                f"`{disk.path or disk.name}` "
                f"size=`{disk.size or 'unknown'}` "
                f"transport=`{disk.transport or 'unknown'}` "
                f"efi=`{_format_bool(disk.has_efi_partition)}` "
                f"windows=`{_format_bool(disk.has_windows_markers)}`"
            )
        lines.append("")

    lines.append("## Command risk counts")
    lines.append(f"- Safe commands: `{safe_count}`")
    lines.append(f"- High-risk commands: `{high_count}`")
    lines.append(f"- Critical commands: `{critical_count}`")
    lines.append("")

    if plan.warnings:
        lines.append("## Warnings")
        for warning in plan.warnings:
            lines.append(f"- {warning}")
        lines.append("")

    lines.append("## Safety boundary")
    lines.append("- This report is read-only.")
    lines.append("- It does not execute installer scripts.")
    lines.append("- It does not choose a target disk.")
    lines.append("- It does not override deterministic risk classification.")

    return "\n".join(lines).rstrip() + "\n"


def _count_commands(plan: InstallPlan, risk: CommandRisk) -> int:
    return sum(1 for step in plan.steps if step.command is not None and step.command.risk == risk)


def _format_bool(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"
