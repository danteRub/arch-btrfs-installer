# AI Advisor CLI

The AI advisor CLI generates conservative installation plans from diagnostic reports.

It does not execute installer commands.

## Basic usage

Generate a Markdown plan:

```bash
python -m ai_advisor diagnostics/system_report.json
```

Generate JSON:

```bash
python -m ai_advisor diagnostics/system_report.json --json
```

Generate a human-readable explanation:

```bash
python -m ai_advisor diagnostics/system_report.json --explain
```

Generate a concise health report:

```bash
python -m ai_advisor diagnostics/system_report.json --doctor
```

Generate a complete report bundle:

```bash
python -m ai_advisor diagnostics/system_report.json --bundle out/
```

`--explain` is deterministic. It summarizes risks and review steps without changing commands, warnings or risk labels.

`--doctor` is deterministic and read-only. It summarizes system signals, plan status, command risk counts and warnings.

`--bundle` is deterministic and read-only. It writes multiple report files to a directory.

`--json`, `--explain`, `--doctor` and `--bundle` are mutually exclusive.

## Plan status

Generated plans include a top-level status:

| Status | Meaning |
| --- | --- |
| `ready` | No blocking conditions or warnings were detected. |
| `needs_review` | The plan can be reviewed but contains warnings, critical commands or other manual-review signals. |
| `blocked` | The advisor cannot safely produce an actionable plan because a required precondition is missing, such as boot mode or disk candidates. |

Markdown output includes a `## Status` section.

JSON output includes:

```json
{
  "status": "needs_review",
  "status_reasons": [
    "Plan contains critical commands that require explicit human confirmation."
  ]
}
```

## Doctor mode

Doctor mode provides a short operational health report:

```bash
python -m ai_advisor diagnostics/system_report.json --doctor
```

It includes:

- overall plan status,
- status reasons,
- boot mode,
- CPU vendor,
- microcode package,
- network signal,
- disk candidates,
- EFI detection,
- Windows/NTFS marker detection,
- command risk counts,
- warnings,
- safety boundary reminders.

## Bundle mode

Bundle mode creates a portable report directory:

```bash
python -m ai_advisor diagnostics/system_report.json --bundle out/
```

Generated files:

```text
out/
  system_report.json
  plan.md
  plan.json
  doctor.md
  explanation.md
  summary.txt
```

Bundle mode cannot be combined with `--output`, because the bundle path is already the output target.

## Write output to a file

Markdown:

```bash
python -m ai_advisor diagnostics/system_report.json --output plan.md
```

JSON:

```bash
python -m ai_advisor diagnostics/system_report.json --json --output plan.json
```

Explanation:

```bash
python -m ai_advisor diagnostics/system_report.json --explain --output explanation.md
```

Doctor report:

```bash
python -m ai_advisor diagnostics/system_report.json --doctor --output doctor.md
```

## Automation controls

### Strict mode

```bash
python -m ai_advisor diagnostics/system_report.json --strict
```

Returns exit code `2` when the generated plan contains warnings.

Use this when warnings should block an automated workflow.

### Fail on critical commands

```bash
python -m ai_advisor diagnostics/system_report.json --fail-on-critical
```

Returns exit code `3` when the generated plan contains commands classified as `critical`.

Use this when critical commands should force human review before continuing.

### Combined mode

```bash
python -m ai_advisor diagnostics/system_report.json --strict --fail-on-critical
```

If both conditions are true, `--fail-on-critical` takes precedence and returns exit code `3`.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Plan generated successfully. |
| `2` | `--strict` was enabled and the plan contains warnings. |
| `3` | `--fail-on-critical` was enabled and the plan contains critical commands. |

## Example fixture runs

```bash
python -m ai_advisor tests/fixtures/uefi_nvme_amd.json
python -m ai_advisor tests/fixtures/uefi_windows_dualboot.json
python -m ai_advisor tests/fixtures/multiple_disks.json --strict
python -m ai_advisor tests/fixtures/uefi_nvme_amd.json --fail-on-critical
python -m ai_advisor tests/fixtures/uefi_windows_dualboot.json --explain
python -m ai_advisor tests/fixtures/multiple_disks.json --doctor
python -m ai_advisor tests/fixtures/uefi_nvme_amd.json --bundle tmp/advisor-bundle
```

## Safety boundary

The CLI renders a plan, explanation, doctor report, report bundle or JSON payload and returns exit codes. It must not:

- execute installer scripts,
- partition disks,
- format filesystems,
- modify boot records,
- override deterministic risk classification,
- remove warnings from the generated plan.
