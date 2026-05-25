# AI Engineering Implementation Plan

This document defines how `arch-btrfs-installer` should evolve from a script-based installer into a safe AI-assisted installation advisor.

## Core principle

The AI layer is advisory. It must not directly execute destructive operations.

The installer may contain destructive commands, but the advisor must produce plans, explanations, risk labels and validation checks.

## Architecture

```text
scripts/diagnostics.sh
        |
        v
diagnostics/system_report.json
        |
        v
ai_advisor.hardware_parser
        |
        v
ai_advisor.planner
        |
        v
ai_advisor.risk_classifier
        |
        v
human-readable installation plan
```

## Proposed Python package

```text
ai_advisor/
  __init__.py
  models.py
  hardware_parser.py
  planner.py
  risk_classifier.py
  prompts.py
  evals/
    fixtures/
    expected/
```

## Data contracts

### SystemReport

Minimum fields:

```json
{
  "schema_version": "0.1.0",
  "system": {
    "boot_mode": "UEFI",
    "cpu_vendor": "AuthenticAMD",
    "network_link_up_detected": "yes"
  },
  "commands": {
    "lsblk_json": "...",
    "lscpu_json": "...",
    "lspci": "..."
  }
}
```

### InstallPlan

Minimum fields:

```json
{
  "summary": "UEFI NVMe Btrfs install with systemd-boot",
  "assumptions": [],
  "warnings": [],
  "steps": [
    {
      "title": "Format selected root partition",
      "command": "mkfs.btrfs -f -L ArchRoot /dev/nvme0n1p2",
      "risk": "critical",
      "requires_confirmation": true,
      "reason": "This destroys data on the selected partition."
    }
  ]
}
```

## Risk classifier

| Pattern | Risk | Required behavior |
| --- | --- | --- |
| `lsblk`, `lscpu`, `lspci`, `findmnt`, `ip link`, `timedatectl` | `safe` | May be shown freely. |
| `pacstrap`, `pacman -S`, `systemctl enable` | `high` | Explain system state change. |
| `mount`, `umount`, `arch-chroot` | `high` | Explain target and preconditions. |
| `wipefs`, `sgdisk`, `parted`, `mkfs.*` | `critical` | Require explicit confirmation. |
| `bootctl install`, `grub-install` | `critical` | Require explicit confirmation and boot mode validation. |

## Evaluation scenarios

Create fixtures for:

1. UEFI + NVMe + AMD CPU.
2. UEFI + SATA + Intel CPU.
3. BIOS + SATA.
4. UEFI + Windows dual boot detected.
5. Existing ESP but no mounted `/mnt/boot`.
6. No network link.
7. Unknown CPU vendor.
8. Multiple disks where one appears to contain an existing OS.

## Required tests

The advisor must:

- Never classify `mkfs.*`, `wipefs`, `sgdisk` or `parted` below `critical`.
- Never recommend wiping a disk without explicit warning.
- Detect UEFI/BIOS from the report.
- Recommend `amd-ucode` for `AuthenticAMD` and `intel-ucode` for `GenuineIntel`.
- Warn when Windows boot files appear in an EFI partition.
- Produce valid JSON for machine-readable plans.
- Produce a concise human-readable summary.

## Portfolio value

This project demonstrates:

- Linux automation.
- Safety-aware AI system design.
- Structured diagnostics.
- Risk classification.
- Testable LLM workflows.
- Human-in-the-loop execution.
- Clear boundary between recommendation and execution.

## Next implementation step

Add `ai_advisor/models.py` and `ai_advisor/risk_classifier.py`, then test the classifier without calling any LLM API.
