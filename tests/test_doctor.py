from ai_advisor import create_initial_plan, render_doctor_report
from ai_advisor.hardware_parser import DiskCandidate, HardwareSummary


def test_doctor_report_summarizes_basic_system_signals() -> None:
    summary = HardwareSummary(
        boot_mode="UEFI",
        cpu_vendor="AuthenticAMD",
        microcode_package="amd-ucode",
        network_link_up=True,
        disks=[DiskCandidate(name="nvme0n1", path="/dev/nvme0n1", size="1T", transport="nvme", has_efi_partition=True)],
    )
    plan = create_initial_plan(summary)

    report = render_doctor_report(summary, plan)

    assert "# Advisor doctor report" in report
    assert "Status: `needs_review`" in report
    assert "Boot mode: `UEFI`" in report
    assert "CPU vendor: `AuthenticAMD`" in report
    assert "Microcode package: `amd-ucode`" in report
    assert "Network link detected: `yes`" in report
    assert "Disk candidates: `1`" in report
    assert "EFI partition detected: `yes`" in report
    assert "Critical commands: `1`" in report


def test_doctor_report_highlights_windows_markers() -> None:
    summary = HardwareSummary(
        boot_mode="UEFI",
        cpu_vendor="GenuineIntel",
        microcode_package="intel-ucode",
        network_link_up=True,
        disks=[DiskCandidate(name="sda", path="/dev/sda", has_efi_partition=True, has_windows_markers=True)],
        possible_windows_dual_boot=True,
        warnings=["Windows or NTFS markers were detected; avoid wiping disks without review."],
    )
    plan = create_initial_plan(summary)

    report = render_doctor_report(summary, plan)

    assert "Windows/NTFS markers detected: `yes`" in report
    assert "Possible Windows dual-boot" in report
    assert "Windows or NTFS markers" in report


def test_doctor_report_marks_blocked_plan() -> None:
    summary = HardwareSummary(
        boot_mode="unknown",
        cpu_vendor="unknown",
        microcode_package=None,
        network_link_up=None,
        disks=[],
    )
    plan = create_initial_plan(summary)

    report = render_doctor_report(summary, plan)

    assert "Status: `blocked`" in report
    assert "Planning is blocked" in report
    assert "Boot mode is unknown" in report
    assert "Disk candidates: `0`" in report
