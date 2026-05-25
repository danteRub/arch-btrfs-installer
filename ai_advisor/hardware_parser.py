from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .models import SystemReport


@dataclass(frozen=True)
class DiskCandidate:
    """A physical disk detected from lsblk JSON output."""

    name: str
    path: str | None = None
    size: str | None = None
    model: str | None = None
    transport: str | None = None
    removable: bool | None = None
    has_partitions: bool = False
    has_efi_partition: bool = False
    has_windows_markers: bool = False


@dataclass(frozen=True)
class HardwareSummary:
    """Normalized facts used by the future planner."""

    boot_mode: str
    cpu_vendor: str
    microcode_package: str | None
    network_link_up: bool | None
    disks: list[DiskCandidate] = field(default_factory=list)
    possible_windows_dual_boot: bool = False
    warnings: list[str] = field(default_factory=list)


def _parse_json_string(value: str) -> Any:
    """Parse a command output stored as a JSON string.

    diagnostics.sh stores command outputs as escaped strings. Some command outputs,
    such as `lsblk --json`, are themselves JSON. This helper parses that inner JSON.
    """

    if not value or value.startswith("COMMAND_FAILED:"):
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _microcode_package(cpu_vendor: str) -> str | None:
    normalized = cpu_vendor.strip().lower()

    if normalized == "authenticamd":
        return "amd-ucode"
    if normalized == "genuineintel":
        return "intel-ucode"
    return None


def _network_link_up(value: str) -> bool | None:
    normalized = value.strip().lower()

    if normalized == "yes":
        return True
    if normalized == "no":
        return False
    return None


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes"}:
            return True
        if normalized in {"0", "false", "no"}:
            return False
    return None


def _walk_block_devices(devices: list[dict[str, Any]]) -> list[DiskCandidate]:
    candidates: list[DiskCandidate] = []

    for device in devices:
        if device.get("type") != "disk":
            continue

        children = device.get("children") or []
        has_efi = False
        has_windows = False

        for child in children:
            fstype = str(child.get("fstype") or "").lower()
            parttype = str(child.get("parttype") or "").lower()
            label = str(child.get("label") or "").lower()
            partlabel = str(child.get("partlabel") or "").lower()
            mountpoint = str(child.get("mountpoint") or "").lower()

            if fstype in {"vfat", "fat32", "fat16"} and (
                parttype.endswith("ef00")
                or "efi" in label
                or "efi" in partlabel
                or mountpoint.endswith("/boot")
                or mountpoint.endswith("/boot/efi")
            ):
                has_efi = True

            if (
                "microsoft" in label
                or "microsoft" in partlabel
                or "windows" in label
                or "windows" in partlabel
                or fstype == "ntfs"
            ):
                has_windows = True

        candidates.append(
            DiskCandidate(
                name=str(device.get("name") or "unknown"),
                path=device.get("path"),
                size=device.get("size"),
                model=device.get("model"),
                transport=device.get("tran"),
                removable=_as_bool(device.get("rm")),
                has_partitions=bool(children),
                has_efi_partition=has_efi,
                has_windows_markers=has_windows,
            )
        )

    return candidates


def summarize_hardware(report: SystemReport) -> HardwareSummary:
    """Convert a raw diagnostic report into planner-friendly facts."""

    warnings: list[str] = []
    boot_mode = report.system.boot_mode.upper()
    cpu_vendor = report.system.cpu_vendor
    microcode = _microcode_package(cpu_vendor)
    network_up = _network_link_up(report.system.network_link_up_detected)

    if boot_mode not in {"UEFI", "BIOS"}:
        warnings.append("Boot mode is unknown; bootloader recommendations require manual review.")

    if microcode is None:
        warnings.append("CPU vendor is not Intel or AMD; no microcode package can be inferred.")

    if network_up is False:
        warnings.append("No active network link was detected; pacstrap may fail without connectivity.")
    elif network_up is None:
        warnings.append("Network state is unknown; verify connectivity before installation.")

    lsblk_output = report.commands.get("lsblk_json", "")
    parsed_lsblk = _parse_json_string(lsblk_output)
    block_devices = []
    if isinstance(parsed_lsblk, dict):
        block_devices = parsed_lsblk.get("blockdevices") or []

    disks = _walk_block_devices(block_devices)

    if not disks:
        warnings.append("No disk candidates were parsed from lsblk output.")

    possible_windows = any(disk.has_windows_markers for disk in disks)
    if possible_windows:
        warnings.append("Windows or NTFS markers were detected; avoid wiping disks without review.")

    if boot_mode == "UEFI" and disks and not any(disk.has_efi_partition for disk in disks):
        warnings.append("UEFI mode detected but no EFI partition was identified in lsblk output.")

    return HardwareSummary(
        boot_mode=boot_mode,
        cpu_vendor=cpu_vendor,
        microcode_package=microcode,
        network_link_up=network_up,
        disks=disks,
        possible_windows_dual_boot=possible_windows,
        warnings=warnings,
    )
