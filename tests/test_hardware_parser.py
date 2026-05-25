import json

from ai_advisor import SystemReport, summarize_hardware


def _report(*, boot_mode: str, cpu_vendor: str, network: str, blockdevices: list[dict]) -> SystemReport:
    return SystemReport(
        schema_version="0.1.0",
        system={
            "boot_mode": boot_mode,
            "cpu_vendor": cpu_vendor,
            "network_link_up_detected": network,
        },
        commands={
            "lsblk_json": json.dumps({"blockdevices": blockdevices}),
        },
    )


def test_summarize_uefi_nvme_amd_with_efi_partition() -> None:
    report = _report(
        boot_mode="UEFI",
        cpu_vendor="AuthenticAMD",
        network="yes",
        blockdevices=[
            {
                "name": "nvme0n1",
                "path": "/dev/nvme0n1",
                "type": "disk",
                "size": "1T",
                "model": "Fast NVMe",
                "tran": "nvme",
                "rm": False,
                "children": [
                    {
                        "name": "nvme0n1p1",
                        "type": "part",
                        "fstype": "vfat",
                        "parttype": "ef00",
                        "partlabel": "EFI",
                    },
                    {
                        "name": "nvme0n1p2",
                        "type": "part",
                        "fstype": "btrfs",
                        "partlabel": "Linux_BTRFS",
                    },
                ],
            }
        ],
    )

    summary = summarize_hardware(report)

    assert summary.boot_mode == "UEFI"
    assert summary.microcode_package == "amd-ucode"
    assert summary.network_link_up is True
    assert len(summary.disks) == 1
    assert summary.disks[0].has_efi_partition is True
    assert summary.possible_windows_dual_boot is False
    assert summary.warnings == []


def test_summarize_intel_cpu_microcode() -> None:
    report = _report(
        boot_mode="BIOS",
        cpu_vendor="GenuineIntel",
        network="yes",
        blockdevices=[],
    )

    summary = summarize_hardware(report)

    assert summary.microcode_package == "intel-ucode"
    assert "No disk candidates" in " ".join(summary.warnings)


def test_windows_or_ntfs_markers_raise_dual_boot_warning() -> None:
    report = _report(
        boot_mode="UEFI",
        cpu_vendor="AuthenticAMD",
        network="yes",
        blockdevices=[
            {
                "name": "sda",
                "path": "/dev/sda",
                "type": "disk",
                "size": "512G",
                "children": [
                    {
                        "name": "sda1",
                        "type": "part",
                        "fstype": "vfat",
                        "parttype": "ef00",
                        "partlabel": "EFI",
                    },
                    {
                        "name": "sda2",
                        "type": "part",
                        "fstype": "ntfs",
                        "partlabel": "Microsoft basic data",
                    },
                ],
            }
        ],
    )

    summary = summarize_hardware(report)

    assert summary.possible_windows_dual_boot is True
    assert summary.disks[0].has_windows_markers is True
    assert any("Windows or NTFS" in warning for warning in summary.warnings)


def test_uefi_without_efi_partition_warns() -> None:
    report = _report(
        boot_mode="UEFI",
        cpu_vendor="AuthenticAMD",
        network="yes",
        blockdevices=[
            {
                "name": "sda",
                "path": "/dev/sda",
                "type": "disk",
                "children": [
                    {"name": "sda1", "type": "part", "fstype": "ext4"},
                ],
            }
        ],
    )

    summary = summarize_hardware(report)

    assert any("no EFI partition" in warning for warning in summary.warnings)


def test_no_network_link_warns() -> None:
    report = _report(
        boot_mode="UEFI",
        cpu_vendor="AuthenticAMD",
        network="no",
        blockdevices=[],
    )

    summary = summarize_hardware(report)

    assert summary.network_link_up is False
    assert any("No active network link" in warning for warning in summary.warnings)
