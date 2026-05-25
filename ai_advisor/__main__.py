from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .doctor import render_doctor_report
from .explainer import explain_plan
from .hardware_parser import HardwareSummary, summarize_hardware
from .llm_explainer import explain_plan_with_optional_llm
from .models import CommandRisk, InstallPlan, SystemReport
from .openai_compatible import OpenAICompatibleClient, OpenAICompatibleClientError
from .planner import create_initial_plan


_RISK_ICON = {
    CommandRisk.SAFE: "[safe]",
    CommandRisk.MEDIUM: "[medium]",
    CommandRisk.HIGH: "[high]",
    CommandRisk.CRITICAL: "[critical]",
}


def _load_report(path: Path) -> SystemReport:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Diagnostic report not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON report: {path}: {exc}") from exc

    try:
        return SystemReport.model_validate(raw)
    except ValidationError as exc:
        raise SystemExit(f"Report does not match SystemReport schema:\n{exc}") from exc


def _render_plan(plan: InstallPlan) -> str:
    lines: list[str] = []

    lines.append("# Arch Btrfs AI Advisor")
    lines.append("")
    lines.append("## Summary")
    lines.append(plan.summary)
    lines.append("")

    lines.append("## Status")
    lines.append(f"- Status: `{plan.status.value}`")
    for reason in plan.status_reasons:
        lines.append(f"- {reason}")
    lines.append("")

    if plan.assumptions:
        lines.append("## Assumptions")
        for assumption in plan.assumptions:
            lines.append(f"- {assumption}")
        lines.append("")

    if plan.warnings:
        lines.append("## Warnings")
        for warning in plan.warnings:
            lines.append(f"- {warning}")
        lines.append("")

    lines.append("## Steps")
    for index, step in enumerate(plan.steps, start=1):
        lines.append(f"{index}. {step.title}")
        lines.append(f"   {step.description}")
        if step.command is not None:
            icon = _RISK_ICON[step.command.risk]
            confirm = "requires confirmation" if step.command.requires_confirmation else "no confirmation required"
            lines.append(f"   - Command: `{step.command.command}`")
            lines.append(f"   - Risk: {icon} {step.command.risk.value} ({confirm})")
            lines.append(f"   - Reason: {step.command.reason}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_bundle_summary(summary: HardwareSummary, plan: InstallPlan) -> str:
    critical_count = sum(
        1 for step in plan.steps if step.command is not None and step.command.risk == CommandRisk.CRITICAL
    )
    high_count = sum(
        1 for step in plan.steps if step.command is not None and step.command.risk == CommandRisk.HIGH
    )
    return (
        "Arch Btrfs AI Advisor bundle\n"
        "=============================\n\n"
        f"Status: {plan.status.value}\n"
        f"Boot mode: {summary.boot_mode}\n"
        f"CPU vendor: {summary.cpu_vendor}\n"
        f"Microcode package: {summary.microcode_package or 'unknown'}\n"
        f"Network link detected: {summary.network_link_up}\n"
        f"Disk candidates: {len(summary.disks)}\n"
        f"Warnings: {len(plan.warnings)}\n"
        f"High-risk commands: {high_count}\n"
        f"Critical commands: {critical_count}\n\n"
        "Generated files:\n"
        "- system_report.json\n"
        "- plan.md\n"
        "- plan.json\n"
        "- doctor.md\n"
        "- explanation.md\n"
        "- summary.txt\n"
    )


def _write_bundle(
    output_dir: Path,
    report: SystemReport,
    summary: HardwareSummary,
    plan: InstallPlan,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "system_report.json").write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    (output_dir / "plan.md").write_text(_render_plan(plan), encoding="utf-8")
    (output_dir / "plan.json").write_text(plan.model_dump_json(indent=2) + "\n", encoding="utf-8")
    (output_dir / "doctor.md").write_text(render_doctor_report(summary, plan), encoding="utf-8")
    (output_dir / "explanation.md").write_text(explain_plan(plan), encoding="utf-8")
    (output_dir / "summary.txt").write_text(_render_bundle_summary(summary, plan), encoding="utf-8")


def _has_critical_commands(plan: InstallPlan) -> bool:
    return any(
        step.command is not None and step.command.risk == CommandRisk.CRITICAL
        for step in plan.steps
    )


def _has_warnings(plan: InstallPlan) -> bool:
    return bool(plan.warnings)


def _write_or_print(content: str, output: Path | None) -> None:
    if output is None:
        print(content, end="")
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")


def _build_llm_client(provider: str | None):
    if provider is None:
        return None

    if provider == "openai-compatible":
        try:
            return OpenAICompatibleClient.from_env()
        except OpenAICompatibleClientError as exc:
            raise SystemExit(str(exc)) from exc

    raise SystemExit(f"Unsupported LLM provider: {provider}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create a conservative Arch Btrfs installation plan from diagnostics JSON."
    )
    parser.add_argument(
        "report",
        type=Path,
        help="Path to diagnostics/system_report.json generated by scripts/diagnostics.sh.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the generated InstallPlan as JSON instead of Markdown.",
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help="Print a human-readable explanation instead of the raw plan.",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Print a concise read-only health report for the diagnostic and generated plan.",
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        help="Write a complete read-only report bundle to the given directory.",
    )
    parser.add_argument(
        "--llm-provider",
        choices=["openai-compatible"],
        help="Optional LLM provider used only with --explain. Requires provider-specific env vars.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the generated plan to a file instead of stdout.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 2 when the plan contains warnings.",
    )
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Return exit code 3 when the plan contains critical commands.",
    )

    args = parser.parse_args(argv)

    selected_modes = sum(bool(mode) for mode in (args.json, args.explain, args.doctor, args.bundle))
    if selected_modes > 1:
        raise SystemExit("--json, --explain, --doctor and --bundle are mutually exclusive")

    if args.llm_provider and not args.explain:
        raise SystemExit("--llm-provider requires --explain")

    if args.bundle and args.output:
        raise SystemExit("--bundle cannot be used with --output")

    report = _load_report(args.report)
    summary = summarize_hardware(report)
    plan = create_initial_plan(summary)

    if args.bundle:
        _write_bundle(args.bundle, report, summary, plan)
        rendered = f"Bundle written to {args.bundle}\n"
    elif args.json:
        rendered = plan.model_dump_json(indent=2) + "\n"
    elif args.explain:
        client = _build_llm_client(args.llm_provider)
        if client is None:
            rendered = explain_plan(plan)
        else:
            rendered = explain_plan_with_optional_llm(plan, client=client).explanation
    elif args.doctor:
        rendered = render_doctor_report(summary, plan)
    else:
        rendered = _render_plan(plan)

    _write_or_print(rendered, None if args.bundle else args.output)

    if args.fail_on_critical and _has_critical_commands(plan):
        return 3

    if args.strict and _has_warnings(plan):
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
