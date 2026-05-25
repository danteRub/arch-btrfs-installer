from ai_advisor import CommandRisk, create_initial_plan
from ai_advisor.hardware_parser import DiskCandidate, HardwareSummary


def test_initial_plan_contains_expected_uefi_amd_summary() -> None:
    summary = HardwareSummary(
        boot_mode="UEFI",
        cpu_vendor="AuthenticAMD",
        microcode_package="amd-ucode",
        network_link_up=True,
        disks=[
            DiskCandidate(
                name="nvme0n1",
                path="/dev/nvme0n1",
                has_partitions=True,
                has_efi_partition=True,
            )
        ],
    )

    plan = create_initial_plan(summary)

    assert "UEFI" in plan.summary
    assert "amd-ucode" in plan.summary
    assert any("systemd-boot" in assumption for assumption in plan.assumptions)
    assert len(plan.steps) >= 4


def test_windows_dual_boot_adds_warning() -> None:
    summary = HardwareSummary(
        boot_mode="UEFI",
        cpu_vendor="AuthenticAMD",
        microcode_package="amd-ucode",
        network_link_up=True,
        disks=[DiskCandidate(name="sda", has_windows_markers=True)],
        possible_windows_dual_boot=True,
    )

    plan = create_initial_plan(summary)

    assert any("Windows" in warning for warning in plan.warnings)
    assert any("Do not wipe" in warning for warning in plan.warnings)


def test_multiple_disks_require_explicit_selection() -> None:
    summary = HardwareSummary(
        boot_mode="UEFI",
        cpu_vendor="GenuineIntel",
        microcode_package="intel-ucode",
        network_link_up=True,
        disks=[DiskCandidate(name="sda"), DiskCandidate(name="nvme0n1")],
    )

    plan = create_initial_plan(summary)

    assert any("Multiple disk" in warning for warning in plan.warnings)


def test_no_network_adds_verification_step() -> None:
    summary = HardwareSummary(
        boot_mode="UEFI",
        cpu_vendor="AuthenticAMD",
        microcode_package="amd-ucode",
        network_link_up=False,
        disks=[DiskCandidate(name="sda")],
    )

    plan = create_initial_plan(summary)

    assert any(step.title == "Verify network before pacstrap" for step in plan.steps)


def test_local_installer_scripts_are_classified_conservatively() -> None:
    summary = HardwareSummary(
        boot_mode="UEFI",
        cpu_vendor="AuthenticAMD",
        microcode_package="amd-ucode",
        network_link_up=True,
        disks=[DiskCandidate(name="sda")],
    )

    plan = create_initial_plan(summary)
    commands = [step.command for step in plan.steps if step.command is not None]

    installer_command = next(command for command in commands if command.command == "./01-installer.sh")
    pacstrap_command = next(command for command in commands if command.command == "./02-pacstrap.sh")

    assert installer_command.risk == CommandRisk.CRITICAL
    assert pacstrap_command.risk == CommandRisk.HIGH
    assert installer_command.requires_confirmation is True
    assert pacstrap_command.requires_confirmation is True


def test_read_only_review_steps_are_safe() -> None:
    summary = HardwareSummary(
        boot_mode="UEFI",
        cpu_vendor="AuthenticAMD",
        microcode_package="amd-ucode",
        network_link_up=True,
        disks=[DiskCandidate(name="sda")],
    )

    plan = create_initial_plan(summary)
    read_only_commands = {
        step.command.command: step.command
        for step in plan.steps
        if step.command is not None and step.command.command in {"lsblk --json -O", "efibootmgr -v"}
    }

    assert read_only_commands["lsblk --json -O"].risk == CommandRisk.SAFE
    assert read_only_commands["efibootmgr -v"].risk == CommandRisk.SAFE
