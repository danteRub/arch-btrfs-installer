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

See [`docs/SAFETY.md`](docs/SAFETY.md) for the full project safety policy.

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

Then generate a conservative installation plan:

```bash
python -m ai_advisor diagnostics/system_report.json
```

JSON output is also available:

```bash
python -m ai_advisor diagnostics/system_report.json --json
```

The current pipeline is:

```text
system_report.json -> hardware parser -> deterministic planner -> risk classifier -> human approval
```

## Example outputs

Pre-generated examples are available for quick review:

| Scenario | Output |
| --- | --- |
| UEFI + NVMe + AMD CPU | [`examples/uefi_nvme_amd.md`](examples/uefi_nvme_amd.md) |
| UEFI + Windows dual boot markers | [`examples/uefi_windows_dualboot.md`](examples/uefi_windows_dualboot.md) |

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest -q
```

Try the CLI with included fixtures:

```bash
python -m ai_advisor tests/fixtures/uefi_nvme_amd.json
python -m ai_advisor tests/fixtures/uefi_windows_dualboot.json
```

## AI Engineering modules

```text
ai_advisor/
  models.py          # Pydantic schemas
  hardware_parser.py # Parse diagnostics JSON
  risk_classifier.py # Classify generated commands
  planner.py         # Generate deterministic install plans
  __main__.py        # CLI entrypoint
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Contributions that touch installer or advisor safety logic must include tests.

## Roadmap

1. Add read-only diagnostics exporter.
2. Add sample fixtures for UEFI, BIOS, NVMe, SATA, AMD, Intel and dual-boot scenarios.
3. Add Python schemas with Pydantic.
4. Add command risk classifier.
5. Add a deterministic advisor that generates plans, not commands to execute blindly.
6. Add tests and CI.
7. Add optional LLM planning behind the deterministic parser/classifier boundary.
8. Add documentation explaining failure modes and rollback strategy.

## Usage warning

Review every destructive command before running this installer. In particular, commands using `wipefs`, `sgdisk`, `mkfs.*`, `parted`, `mount`, `umount` and bootloader writes must be treated as high-risk or critical operations.
