from __future__ import annotations

from .hardware_parser import HardwareSummary
from .models import InstallPlan, InstallStep
from .risk_classifier import classify_command


def _bootloader_name(summary: HardwareSummary) -> str:
    if summary.boot_mode == "UEFI":
        return "systemd-boot"
    if summary.boot_mode == "BIOS":
        return "manual GRUB review"
    return "manual bootloader review"


def create_initial_plan(summary: HardwareSummary) -> InstallPlan:
    """Create a conservative install plan from normalized hardware facts.

    This planner is deterministic and intentionally cautious. It does not choose
    a disk to wipe. It prepares review steps and marks destructive examples as
    critical through the shared risk classifier.
    """

    assumptions: list[str] = []
    warnings = list(summary.warnings)
    steps: list[InstallStep] = []

    bootloader = _bootloader_name(summary)
    microcode = summary.microcode_package or "no inferred microcode package"

    assumptions.append(f"Boot mode detected as {summary.boot_mode}.")
    assumptions.append(f"CPU vendor detected as {summary.cpu_vendor}; microcode: {microcode}.")
    assumptions.append(f"Recommended bootloader path: {bootloader}.")

    if summary.possible_windows_dual_boot:
        warnings.append(
            "Possible Windows dual-boot detected. Do not wipe any disk until the target disk "
            "and EFI partition have been manually verified."
        )

    if not summary.disks:
        warnings.append("No disk candidates are available; installation planning cannot select storage.")
    elif len(summary.disks) > 1:
        warnings.append("Multiple disk candidates detected; require explicit user selection.")

    steps.append(
        InstallStep(
            title="Collect system diagnostics",
            description="Generate a read-only diagnostic report before planning installation.",
            command=classify_command("./scripts/diagnostics.sh"),
        )
    )

    steps.append(
        InstallStep(
            title="Review block devices",
            description="Inspect disks, partitions, filesystems and existing operating system markers.",
            command=classify_command("lsblk --json -O"),
        )
    )

    if summary.boot_mode == "UEFI":
        steps.append(
            InstallStep(
                title="Verify EFI system partition",
                description="Confirm whether an existing ESP should be reused or a new one must be created.",
                command=classify_command("efibootmgr -v"),
            )
        )

    if summary.network_link_up is not True:
        steps.append(
            InstallStep(
                title="Verify network before pacstrap",
                description="Arch installation requires working package mirrors and network connectivity.",
                command=classify_command("ip link show"),
            )
        )

    steps.append(
        InstallStep(
            title="Run partitioning script only after manual confirmation",
            description=(
                "This script may wipe, partition and format storage. Review selected disk and mode "
                "before continuing."
            ),
            command=classify_command("./01-installer.sh"),
        )
    )

    steps.append(
        InstallStep(
            title="Install base system after /mnt is mounted",
            description=(
                "Run pacstrap and system configuration only after the target Btrfs layout is mounted "
                "under /mnt."
            ),
            command=classify_command("./02-pacstrap.sh"),
        )
    )

    summary_text = (
        f"{summary.boot_mode} installation plan using Btrfs with {bootloader}; "
        f"microcode recommendation: {microcode}."
    )

    return InstallPlan(
        summary=summary_text,
        assumptions=assumptions,
        warnings=warnings,
        steps=steps,
    )
