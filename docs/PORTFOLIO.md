# AI Engineering Portfolio Case Study

## Project

**Arch Btrfs Installer Advisor**

A safety-aware AI Engineering project built around an Arch Linux Btrfs installer.

The goal is not to let an LLM install Arch unattended. The goal is to build a trustworthy advisory layer that can inspect a system, generate structured installation plans, classify command risk and optionally explain those plans through an LLM without bypassing deterministic safety controls.

## Problem

Linux installation scripts can be dangerous because they often include commands that can wipe disks, format partitions or alter boot records.

An AI assistant can make this risk worse if it:

- invents hardware details,
- assumes the wrong target disk,
- hides uncertainty,
- generates destructive commands,
- encourages unattended execution,
- fails to detect Windows or dual-boot setups.

This project treats those risks as first-class engineering constraints.

## Core idea

Use deterministic software engineering for the safety-critical path, then place AI behind that boundary.

```text
read-only diagnostics
  -> structured SystemReport
  -> hardware parser
  -> HardwareSummary
  -> deterministic planner
  -> InstallPlan
  -> risk classifier
  -> deterministic explanation
  -> optional LLM explanation
```

The LLM is never the source of truth for risk.

## What the project demonstrates

### 1. Structured diagnostics

The project includes a read-only diagnostic exporter:

```bash
./scripts/diagnostics.sh
```

It writes:

```text
diagnostics/system_report.json
```

The script is intentionally constrained. It may read system state and write its output file, but it must not partition, format, mount, install packages or modify boot records.

### 2. Typed data contracts

The advisor uses Pydantic models for structured data:

```text
SystemReport
HardwareSummary
InstallPlan
InstallStep
InstallCommand
CommandRisk
```

This avoids treating AI output as unstructured text and makes the pipeline testable.

### 3. Deterministic risk classification

Commands are classified into risk levels:

| Risk | Meaning |
| --- | --- |
| `safe` | Expected read-only command. |
| `medium` | Modifies local files, users or configuration. |
| `high` | Changes installation state, mounts filesystems or installs packages. |
| `critical` | Can destroy data, format filesystems, partition disks or alter boot records. |

Examples:

```text
./scripts/diagnostics.sh -> safe
./01-installer.sh        -> critical
./02-pacstrap.sh         -> high
mkfs.btrfs              -> critical
wipefs                  -> critical
bootctl install         -> critical
lsblk --json -O         -> safe
```

### 4. Human-in-the-loop planning

The planner generates conservative plans and warnings. It does not choose a disk to wipe automatically.

It explicitly warns about:

- Windows/NTFS markers,
- possible dual-boot setups,
- multiple disk candidates,
- missing EFI partitions,
- missing network connectivity before `pacstrap`.

### 5. CLI and automation controls

The project exposes a CLI:

```bash
python -m ai_advisor diagnostics/system_report.json
python -m ai_advisor diagnostics/system_report.json --json
python -m ai_advisor diagnostics/system_report.json --explain
```

Automation controls:

```bash
python -m ai_advisor diagnostics/system_report.json --strict
python -m ai_advisor diagnostics/system_report.json --fail-on-critical
```

Exit codes:

| Code | Meaning |
| --- | --- |
| `0` | Plan generated successfully. |
| `2` | Strict mode found warnings. |
| `3` | Critical command mode found critical commands. |

### 6. Optional LLM integration

The LLM layer is optional and provider-agnostic.

Supported pattern:

```bash
AI_ADVISOR_OPENAI_API_KEY=... \
python -m ai_advisor diagnostics/system_report.json \
  --explain \
  --llm-provider openai-compatible
```

The OpenAI-compatible client can target OpenAI, LiteLLM, vLLM gateways or compatible local proxies.

The LLM output is validated. If it omits important safety signals, the system falls back to the deterministic explanation.

### 7. Testability

The repo includes tests for:

- command risk classification,
- hardware parsing,
- deterministic planning,
- CLI behavior,
- fixture scenarios,
- deterministic explanations,
- optional LLM fallback,
- OpenAI-compatible client behavior using monkeypatched network calls.

No test requires a real API key or network access.

## Architecture

```text
scripts/diagnostics.sh
        |
        v
diagnostics/system_report.json
        |
        v
ai_advisor.models.SystemReport
        |
        v
summarize_hardware()
        |
        v
HardwareSummary
        |
        v
create_initial_plan()
        |
        v
InstallPlan
        |
        v
risk classification + warnings
        |
        v
CLI / deterministic explanation / optional LLM explanation
```

## Safety boundaries

The project draws a hard boundary between:

```text
advice
```

and:

```text
execution
```

The advisor may inspect, explain, classify and recommend.

The advisor must not:

- execute destructive commands,
- choose a target disk automatically,
- downgrade risk labels,
- remove warnings,
- invent hardware details,
- assume a disk is safe to erase.

## Example workflow

```bash
make setup
make test
make diagnose
make plan
make explain
```

With an OpenAI-compatible provider:

```bash
AI_ADVISOR_OPENAI_API_KEY=... make explain-llm
```

With fixtures:

```bash
make plan REPORT=tests/fixtures/uefi_nvme_amd.json PLAN=tmp/plan.md
make explain REPORT=tests/fixtures/uefi_windows_dualboot.json EXPLANATION=tmp/explanation.md
```

## Engineering decisions

### Why not let the LLM generate commands directly?

Because installation commands can destroy data. Risk classification must be deterministic and testable.

### Why use fixtures?

Fixtures make edge cases reproducible. They simulate UEFI, BIOS, Windows dual boot, no-network and multi-disk scenarios without needing real hardware.

### Why OpenAI-compatible instead of provider-specific SDK?

The project should remain lightweight and provider-agnostic. A small protocol and standard-library client are enough for the first integration boundary.

### Why fallback to deterministic explanations?

LLM output can omit critical details. The deterministic explanation is safer and always available.

## Skills demonstrated

- Python packaging
- CLI design
- Pydantic models
- Linux diagnostics
- Safety-aware automation
- Test-driven development
- GitHub Actions CI
- LLM integration boundaries
- Prompt construction
- LLM output validation
- Human-in-the-loop system design
- Provider-agnostic API design

## How to describe this project

Short version:

```text
Built a safety-aware AI advisor for Arch Linux Btrfs installations. The system collects read-only diagnostics, parses hardware state, generates structured install plans, classifies command risk, provides CLI automation controls and supports optional OpenAI-compatible explanations behind deterministic validation and fallback boundaries.
```

More technical version:

```text
Designed and implemented a human-in-the-loop AI Engineering pipeline for a Linux installer. The architecture separates deterministic safety-critical logic from optional LLM explanations using typed data contracts, command risk classification, fixture-based test scenarios, CI, and validated OpenAI-compatible provider integration.
```
