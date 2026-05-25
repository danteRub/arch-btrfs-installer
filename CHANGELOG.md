# Changelog

All notable changes to this project will be documented in this file.

This project follows a pragmatic release format inspired by Keep a Changelog.

## [0.1.0] - 2026-05-25

### Added

- Read-only diagnostics exporter at `scripts/diagnostics.sh`.
- Pydantic data contracts for advisor input and output:
  - `SystemReport`
  - `HardwareSummary`
  - `InstallPlan`
  - `InstallStep`
  - `InstallCommand`
  - `CommandRisk`
  - `PlanStatus`
- Deterministic hardware parser for diagnostic reports.
- Conservative deterministic planner for Arch Btrfs installation review.
- Command risk classifier with `safe`, `medium`, `high` and `critical` labels.
- Plan status evaluation with:
  - `ready`
  - `needs_review`
  - `blocked`
- CLI entrypoint:
  - Markdown plan output
  - JSON plan output
  - deterministic explanation mode
  - doctor mode
  - report bundle mode
  - output-to-file support
  - strict warning exit mode
  - fail-on-critical exit mode
- Deterministic plan explainer.
- Optional LLM explainer boundary with validation and deterministic fallback.
- OpenAI-compatible LLM client using Python standard library only.
- Makefile workflow:
  - `make setup`
  - `make lint`
  - `make test`
  - `make diagnose`
  - `make plan`
  - `make plan-json`
  - `make doctor`
  - `make bundle`
  - `make explain`
  - `make explain-llm`
- Fixture-based tests for UEFI, BIOS, Windows dual boot, multiple disks and no-network scenarios.
- GitHub Actions CI for Ruff and pytest.
- Ruff linting baseline.
- Documentation:
  - `docs/SAFETY.md`
  - `docs/CLI.md`
  - `docs/LLM_EXPLAINER.md`
  - `docs/PORTFOLIO.md`
  - `docs/CV_SNIPPETS.md`
  - `docs/REPO_TOPICS.md`
- Security policy.
- GitHub issue templates and pull request template.
- MIT license.

### Safety

- The advisor does not execute installer scripts.
- The advisor does not automatically choose a disk to wipe.
- Destructive commands are classified as `critical`.
- Optional LLM output cannot override deterministic risk labels.
- Optional LLM output falls back to deterministic explanation if validation fails.
- Diagnostics are intended to be read-only.

### Notes

This is the first portfolio-ready release of the AI advisor layer.

The original installer scripts remain safety-sensitive and must be reviewed manually before use on real hardware.
