# Release Checklist

This document describes the manual release process for the project.

## v0.1.0 checklist

Before tagging:

- [ ] `make lint` passes.
- [ ] `make test` passes.
- [ ] `make plan REPORT=tests/fixtures/uefi_nvme_amd.json` works.
- [ ] `make doctor REPORT=tests/fixtures/uefi_nvme_amd.json` works.
- [ ] `make bundle REPORT=tests/fixtures/uefi_nvme_amd.json BUNDLE=tmp/advisor-bundle` works.
- [ ] `CHANGELOG.md` is updated.
- [ ] README still reflects the current CLI.
- [ ] Safety docs still match implemented behavior.

## Suggested tag

```bash
git tag v0.1.0
git push origin v0.1.0
```

## Suggested GitHub release title

```text
v0.1.0 - Safety-aware AI advisor baseline
```

## Suggested GitHub release notes

```text
First portfolio-ready release of the Arch Btrfs AI Advisor.

Highlights:

- Read-only diagnostics exporter.
- Typed Pydantic data contracts.
- Deterministic hardware parser and planner.
- Command risk classifier.
- Plan status evaluation.
- CLI with Markdown, JSON, explanation, doctor and bundle modes.
- Optional OpenAI-compatible LLM explanations behind validation and fallback.
- Fixture-based tests and GitHub Actions CI.
- Safety, portfolio, LLM, CLI and release documentation.

Safety boundary:

The advisor can inspect, classify, plan and explain. It does not execute destructive installer commands or choose disks automatically.
```

## Post-release

After publishing the release:

- [ ] Confirm the GitHub release points to the expected tag.
- [ ] Confirm the README badge still works.
- [ ] Confirm issue templates render correctly.
- [ ] Consider opening a new milestone for `v0.2.0`.
