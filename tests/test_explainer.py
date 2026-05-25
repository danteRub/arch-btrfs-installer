from ai_advisor import create_initial_plan, explain_command_risk, explain_plan
from ai_advisor.hardware_parser import DiskCandidate, HardwareSummary
from ai_advisor.models import CommandRisk


def _sample_plan():
    summary = HardwareSummary(
        boot_mode="UEFI",
        cpu_vendor="AuthenticAMD",
        microcode_package="amd-ucode",
        network_link_up=True,
        disks=[DiskCandidate(name="nvme0n1", has_efi_partition=True)],
    )
    return create_initial_plan(summary)


def test_explain_plan_includes_risk_overview_and_checklist() -> None:
    explanation = explain_plan(_sample_plan())

    assert "# Plan explanation" in explanation
    assert "## Risk overview" in explanation
    assert "Critical commands" in explanation
    assert "Human review checklist" in explanation
    assert "./01-installer.sh" in explanation
    assert "does not execute commands" in explanation


def test_explain_plan_preserves_warnings() -> None:
    summary = HardwareSummary(
        boot_mode="UEFI",
        cpu_vendor="GenuineIntel",
        microcode_package="intel-ucode",
        network_link_up=True,
        disks=[DiskCandidate(name="sda", has_windows_markers=True)],
        possible_windows_dual_boot=True,
        warnings=["Windows or NTFS markers were detected; avoid wiping disks without review."],
    )
    plan = create_initial_plan(summary)
    explanation = explain_plan(plan)

    assert "Warnings that require attention" in explanation
    assert "Windows or NTFS markers" in explanation
    assert "Do not wipe" in explanation


def test_explain_command_risk_labels_are_stable() -> None:
    assert explain_command_risk(CommandRisk.SAFE) == "read-only"
    assert explain_command_risk(CommandRisk.MEDIUM) == "moderate change"
    assert explain_command_risk(CommandRisk.HIGH) == "installation state change"
    assert explain_command_risk(CommandRisk.CRITICAL) == "destructive or boot-critical operation"
