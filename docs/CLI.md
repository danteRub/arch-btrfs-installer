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

`--explain` is deterministic. It summarizes risks and review steps without changing commands, warnings or risk labels.

`--json` and `--explain` are mutually exclusive.

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
```

## Safety boundary

The CLI renders a plan, explanation or JSON payload and returns exit codes. It must not:

- execute installer scripts,
- partition disks,
- format filesystems,
- modify boot records,
- override deterministic risk classification,
- remove warnings from the generated plan.
