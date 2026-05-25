from __future__ import annotations

import re

from .models import CommandRisk, InstallCommand


_CRITICAL_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"(^|\s)(sudo\s+)?wipefs(\s|$)",
        r"(^|\s)(sudo\s+)?sgdisk(\s|$)",
        r"(^|\s)(sudo\s+)?parted(\s|$).*(mkpart|rm|resizepart|set)",
        r"(^|\s)(sudo\s+)?mkfs\.[a-z0-9_+-]+(\s|$)",
        r"(^|\s)(sudo\s+)?bootctl\s+install(\s|$)",
        r"(^|\s)(sudo\s+)?grub-install(\s|$)",
        r"(^|\s)(sudo\s+)?dd\s+.*\bof=/dev/",
    )
)

_HIGH_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"(^|\s)(sudo\s+)?pacstrap(\s|$)",
        r"(^|\s)(sudo\s+)?pacman\s+-S",
        r"(^|\s)(sudo\s+)?mount(\s|$)",
        r"(^|\s)(sudo\s+)?umount(\s|$)",
        r"(^|\s)(sudo\s+)?arch-chroot(\s|$)",
        r"(^|\s)(sudo\s+)?systemctl\s+(enable|disable|start|stop|restart)(\s|$)",
        r"(^|\s)(sudo\s+)?genfstab(\s|$)",
    )
)

_MEDIUM_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"(^|\s)(sudo\s+)?mkdir(\s|$)",
        r"(^|\s)(sudo\s+)?cp(\s|$)",
        r"(^|\s)(sudo\s+)?mv(\s|$)",
        r"(^|\s)(sudo\s+)?tee(\s|$)",
        r"(^|\s)(sudo\s+)?sed\s+-i(\s|$)",
        r"(^|\s)(sudo\s+)?useradd(\s|$)",
        r"(^|\s)(sudo\s+)?passwd(\s|$)",
        r"(^|\s)(sudo\s+)?ln\s+-s",
    )
)

_SAFE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^\s*(sudo\s+)?lsblk(\s|$)",
        r"^\s*(sudo\s+)?lscpu(\s|$)",
        r"^\s*(sudo\s+)?lspci(\s|$)",
        r"^\s*(sudo\s+)?findmnt(\s|$)",
        r"^\s*(sudo\s+)?ip\s+link(\s|$)",
        r"^\s*(sudo\s+)?timedatectl(\s|$)",
        r"^\s*(sudo\s+)?efibootmgr\s+(-v|--verbose)?\s*$",
        r"^\s*(sudo\s+)?uname(\s|$)",
        r"^\s*(sudo\s+)?blkid(\s|$)",
    )
)


def classify_command_text(command: str) -> tuple[CommandRisk, str]:
    """Classify a shell command using deterministic safety rules.

    This intentionally runs before any LLM-based planner. The classifier must be
    conservative: unknown commands are treated as medium risk rather than safe.
    """

    normalized = command.strip()

    if not normalized:
        return CommandRisk.MEDIUM, "Empty command cannot be considered safe."

    for pattern in _CRITICAL_PATTERNS:
        if pattern.search(normalized):
            return (
                CommandRisk.CRITICAL,
                "Command may destroy data, modify partitions or alter boot records.",
            )

    for pattern in _HIGH_PATTERNS:
        if pattern.search(normalized):
            return (
                CommandRisk.HIGH,
                "Command changes installation state, mounts filesystems or modifies the target system.",
            )

    for pattern in _MEDIUM_PATTERNS:
        if pattern.search(normalized):
            return CommandRisk.MEDIUM, "Command modifies files, users or local configuration."

    for pattern in _SAFE_PATTERNS:
        if pattern.search(normalized):
            return CommandRisk.SAFE, "Command is expected to be read-only."

    return CommandRisk.MEDIUM, "Unknown command pattern; classified conservatively."


def classify_command(command: str) -> InstallCommand:
    """Return a structured risk assessment for a command."""

    risk, reason = classify_command_text(command)
    return InstallCommand(
        command=command,
        risk=risk,
        requires_confirmation=risk in {CommandRisk.HIGH, CommandRisk.CRITICAL},
        reason=reason,
    )
