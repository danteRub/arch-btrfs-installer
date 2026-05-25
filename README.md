# Arch Btrfs Installer

Safe, script-based Arch Linux installer focused on Btrfs layouts, UEFI handling, systemd-boot and a clean base system.

This repository is being evolved into an **AI Engineering portfolio project**: an installer assistant that can inspect hardware, produce a structured diagnostic report, classify risky commands and generate auditable installation plans without executing destructive operations automatically.

## Current scripts

| Script | Purpose |
| --- | --- |
| `01-installer.sh` | Select disk, prepare partitions, format Btrfs, create subvolumes and mount the target system under `/mnt`. |
| `02-pacstrap.sh` | Install the base Arch system, configure locale/timezone/user, enable NetworkManager, configure Snapper and install systemd-boot on UEFI systems. |
| `scripts/diagnostics.sh` | Read-only hardware/system diagnostic exporter for future AI-assisted planning. |

## Safety model

The installer scripts can perform destructive operations such as wiping disks and formatting partitions. The AI-related layer must follow a stricter rule:

> AI may explain, inspect, classify and recommend. It must not automatically execute destructive commands.

Command risk classes:

| Risk | Meaning |
| --- | --- |
| `safe` | Read-only operation. |
| `medium` | Changes system state but should not destroy user data. |
| `high` | Boot, mount, package or system configuration changes. |
| `critical` | Formatting, wiping, partitioning, deleting data or changing boot records. |

## First AI-ready workflow

```bash
./scripts/diagnostics.sh
```

This creates:

```text
diagnostics/system_report.json
```

The report is designed to be consumed later by an AI advisor module, for example:

```text
system_report.json -> hardware parser -> risk classifier -> installation plan -> human approval
```

## Planned AI Engineering modules

```text
ai_advisor/
  models.py          # Pydantic schemas
  hardware_parser.py # Parse diagnostics JSON
  risk_classifier.py # Classify generated commands
  planner.py         # Generate installation plan
  evals/             # Test scenarios and expected behavior
```

## Roadmap

1. Add read-only diagnostics exporter.
2. Add sample fixtures for UEFI, BIOS, NVMe, SATA, AMD, Intel and dual-boot scenarios.
3. Add Python schemas with Pydantic.
4. Add command risk classifier.
5. Add an AI advisor that generates plans, not commands to execute blindly.
6. Add tests and CI.
7. Add documentation explaining failure modes and rollback strategy.

## Usage warning

Review every destructive command before running this installer. In particular, commands using `wipefs`, `sgdisk`, `mkfs.*`, `parted`, `mount`, `umount` and bootloader writes must be treated as high-risk or critical operations.
