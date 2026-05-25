# CV and Interview Snippets

This document provides concise descriptions of the project for GitHub, CVs, LinkedIn, interviews and portfolio pages.

## One-line description

```text
Safety-aware AI advisor for Arch Linux Btrfs installations with deterministic diagnostics, risk classification, human-in-the-loop planning and optional OpenAI-compatible explanations.
```

## Short GitHub description

```text
AI-assisted Arch Linux Btrfs installation advisor that collects read-only diagnostics, generates structured plans, classifies command risk and optionally explains plans through a validated OpenAI-compatible LLM boundary.
```

## CV bullet points

```text
- Built a safety-aware AI advisor for Arch Linux installations using Python, Pydantic, CLI tooling and GitHub Actions.
- Designed a deterministic pipeline that converts read-only diagnostics into structured installation plans with command risk classification.
- Implemented human-in-the-loop safety controls for destructive Linux operations such as partitioning, formatting and bootloader changes.
- Added optional OpenAI-compatible LLM explanations behind validation and fallback boundaries, preserving deterministic risk labels and warnings.
- Developed fixture-based tests for UEFI, BIOS, dual-boot, multi-disk and no-network scenarios without requiring real hardware or API keys.
```

## LinkedIn project summary

```text
I built an AI Engineering portfolio project around an Arch Linux Btrfs installer, focusing on safety rather than blind automation. The system collects read-only diagnostics, parses hardware state, generates structured installation plans, classifies risky commands and provides deterministic plus optional LLM explanations. The LLM layer is deliberately placed behind typed data contracts, validation and fallback logic so it can explain plans without changing risk labels or hiding warnings.
```

## Interview explanation: 30 seconds

```text
This project turns a dangerous class of automation, Linux installation scripting, into a safety-aware AI advisor. It does not let the LLM execute commands or choose disks. Instead, it collects read-only diagnostics, creates typed system reports, generates deterministic install plans, classifies commands by risk and optionally uses an OpenAI-compatible LLM only to explain the already-validated plan.
```

## Interview explanation: 2 minutes

```text
The core design decision was to keep the safety-critical path deterministic. The project starts with a read-only diagnostics script that emits JSON. Python then validates that data with Pydantic models, normalizes the hardware state and builds an installation plan. Commands are classified as safe, medium, high or critical using deterministic rules. For example, lsblk is safe, pacstrap is high and mkfs or wipefs are critical.

The optional LLM layer sits after that pipeline. It can explain warnings and summarize risk, but it cannot change commands, remove warnings, downgrade critical operations or invent hardware. If the LLM output omits critical safety signals, the system falls back to the deterministic explanation. This makes the project a practical example of AI Engineering where LLMs are useful, but not trusted as the source of truth.
```

## Architecture answer

```text
The architecture is diagnostics-first: scripts/diagnostics.sh produces a read-only SystemReport JSON. The Python package parses that into HardwareSummary, then create_initial_plan() produces an InstallPlan. The risk classifier annotates commands with deterministic risk labels. The CLI can emit Markdown, JSON, deterministic explanations or optional OpenAI-compatible explanations. Tests cover each layer using fixtures and fake LLM clients.
```

## Safety answer

```text
The main safety boundary is that AI is allowed to inspect, explain and recommend, but not execute. Destructive commands are classified as critical deterministically. The LLM layer is only allowed to explain an existing plan and is validated against warnings and critical commands. If validation fails, the deterministic explanation is used instead.
```

## Testing answer

```text
The project uses fixture-based tests instead of relying on real hardware. There are synthetic diagnostic reports for UEFI, BIOS, Windows dual boot, multiple disks and no-network scenarios. Tests validate parsing, planning, risk classification, CLI output, LLM fallback behavior and OpenAI-compatible client request handling with monkeypatched network calls.
```

## Technical keywords

```text
Python, Pydantic, CLI, pytest, GitHub Actions, Linux diagnostics, Arch Linux, Btrfs, LLMOps, AI safety, human-in-the-loop, OpenAI-compatible API, deterministic planning, risk classification, prompt validation, fallback strategy, fixture-based testing.
```

## What this project proves

```text
- Ability to design LLM systems with safety boundaries.
- Ability to separate deterministic logic from probabilistic AI output.
- Ability to build testable AI workflows.
- Ability to integrate provider-compatible LLM APIs without coupling the core system to a vendor SDK.
- Ability to reason about Linux automation, destructive commands and operational risk.
```

## Suggested repository topics

```text
ai-engineering
llmops
arch-linux
btrfs
linux-automation
human-in-the-loop
pydantic
pytest
openai-compatible
safety
cli
```
