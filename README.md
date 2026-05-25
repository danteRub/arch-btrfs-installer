# Arch Btrfs Installer

[![tests](https://github.com/danteRub/arch-btrfs-installer/actions/workflows/tests.yml/badge.svg)](https://github.com/danteRub/arch-btrfs-installer/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Safety](https://img.shields.io/badge/safety-human--in--the--loop-orange)
![LLM](https://img.shields.io/badge/LLM-optional-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

Safe, script-based Arch Linux installer focused on Btrfs layouts, UEFI handling, systemd-boot and a clean base system.

This repository is being evolved into an **AI Engineering portfolio project**: an installer assistant that can inspect hardware, produce a structured diagnostic report, classify risky commands and generate auditable installation plans without executing destructive operations automatically.

See [`docs/PORTFOLIO.md`](docs/PORTFOLIO.md) for the AI Engineering case study and portfolio summary.

See [`docs/CV_SNIPPETS.md`](docs/CV_SNIPPETS.md) for CV, LinkedIn and interview-ready descriptions.

See [`docs/REPO_TOPICS.md`](docs/REPO_TOPICS.md) for suggested GitHub topics and repository descriptions.

See [`CHANGELOG.md`](CHANGELOG.md) and [`docs/RELEASE.md`](docs/RELEASE.md) for release notes and release checklist.

## Project metadata

| Field | Value |
| --- | --- |
| Domain | Linux automation / AI Engineering |
| Core language | Python 3.11+ and Bash |
| Safety model | Human-in-the-loop advisory system |
| LLM usage | Optional explanation layer only |
| CI | GitHub Actions + pytest |
| Main risk boundary | Deterministic command classification before LLM output |
| License | MIT |

## Current scripts

| Script | Purpose |
| --- | --- |
| `01-installer.sh` | Select disk, prepare partitions, format Btrfs, create subvolumes and mount the target system under `/mnt`. |
| `02-pacstrap.sh` | Install the base Arch system, configure locale/timezone/user, enable NetworkManager, configure Snapper and install systemd-boot on UEFI systems. |
| `scripts/diagnostics.sh` | Read-only hardware/system diagnostic exporter for future AI-assisted planning. |

## Safety model

The installer scripts can perform destructive operations such as wiping disks and formatting partitions. The AI-related layer must follow a stricter rule:

> AI may explain, inspect, classify and recommend. It must not automatically execute destructive commands.

See [`docs/SAFETY.md`](docs/SAFETY.md) and [`SECURITY.md`](SECURITY.md) for the full project safety and reporting policies.

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

Write the generated plan to a file:

```bash
python -m ai_advisor diagnostics/system_report.json --output plan.md
python -m ai_advisor diagnostics/system_report.json --json --output plan.json
```

Automation-oriented exit controls:

```bash
python -m ai_advisor diagnostics/system_report.json --strict
python -m ai_advisor diagnostics/system_report.json --fail-on-critical
```

Exit codes:

| Code | Meaning |
| --- | --- |
| `0` | Plan generated successfully. |
| `2` | `--strict` was enabled and the plan contains warnings. |
| `3` | `--fail-on-critical` was enabled and the plan contains critical commands. |

The current pipeline is:

```text
system_report.json -> hardware parser -> deterministic planner -> risk classifier -> human approval
```

## Make commands

Common commands are available through `make`:

```bash
make help
make setup
make lint
make test
make diagnose
make plan
make plan-json
make doctor
make bundle
make explain
make explain-llm
```

Generated paths can be overridden:

```bash
make plan REPORT=tests/fixtures/uefi_nvme_amd.json PLAN=tmp/plan.md
make explain REPORT=tests/fixtures/uefi_windows_dualboot.json EXPLANATION=tmp/explanation.md
make bundle REPORT=tests/fixtures/uefi_nvme_amd.json BUNDLE=tmp/advisor-bundle
```

`make explain-llm` uses the OpenAI-compatible provider and requires the LLM environment variables described in [`docs/LLM_EXPLAINER.md`](docs/LLM_EXPLAINER.md).

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
make setup
make lint
make test
```

Try the CLI with included fixtures:

```bash
python -m ai_advisor tests/fixtures/uefi_nvme_amd.json
python -m ai_advisor tests/fixtures/uefi_windows_dualboot.json
```

## AI Engineering modules

```text
ai_advisor/
  models.py              # Pydantic schemas
  hardware_parser.py     # Parse diagnostics JSON
  risk_classifier.py     # Classify generated commands
  planner.py             # Generate deterministic install plans
  explainer.py           # Deterministic explanations
  llm_explainer.py       # Optional validated LLM explanation boundary
  openai_compatible.py   # Optional OpenAI-compatible client
  doctor.py              # Read-only doctor report
  __main__.py            # CLI entrypoint
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

## License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE).

## Usage warning

Review every destructive command before running this installer. In particular, commands using `wipefs`, `sgdisk`, `mkfs.*`, `parted`, `mount`, `umount` and bootloader writes must be treated as high-risk or critical operations.
