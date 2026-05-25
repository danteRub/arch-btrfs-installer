# Contributing

This repository contains installer automation and safety-aware AI advisor components. Contributions must preserve the distinction between **advice** and **execution**.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest -q
```

## Before opening a PR

Run:

```bash
pytest -q
```

If you modify shell scripts, manually review that they do not bypass the safety policy in `docs/SAFETY.md`.

## Contribution areas

Good first areas:

- add diagnostic fixtures under `tests/fixtures/`,
- improve parser coverage,
- add regression tests for command risk classification,
- improve CLI output,
- improve documentation,
- add examples under `examples/`.

More advanced areas:

- deterministic planner improvements,
- optional LLM explanation layer,
- structured JSON schemas,
- integration tests using synthetic diagnostics,
- Arch ISO compatibility checks.

## Safety requirements

Any PR touching installer logic or AI advisor logic must answer:

1. Can this change destroy data?
2. Can this change hide or weaken warnings?
3. Can this change classify a dangerous command as safe?
4. Can this change automatically execute something destructive?
5. Does this need a new test?

If the answer to any of the first four questions is yes, the PR must include clear documentation and tests.

## Risk classifier rules

Do not loosen these rules without strong justification and tests:

- `./01-installer.sh` is `critical`.
- `./02-pacstrap.sh` is `high`.
- `wipefs`, `sgdisk`, destructive `parted`, `mkfs.*`, `bootctl install`, `grub-install` and `dd ... of=/dev/...` are `critical`.
- unknown commands are not `safe`.

## LLM-related contributions

LLM features must be optional and must not replace deterministic safety logic.

Acceptable:

- explain a generated plan,
- summarize warnings,
- produce a human-friendly checklist,
- ask the user to clarify disk selection.

Not acceptable:

- execute commands directly,
- choose a disk to erase without confirmation,
- override deterministic risk labels,
- remove warnings about Windows/NTFS/EFI/multiple disks,
- invent hardware details not present in the diagnostic report.

## Commit style

Prefer small commits with concrete messages:

```text
Add fixture for BIOS SATA install
Improve NTFS dual-boot warning
Classify local installer scripts explicitly
```

## Review checklist

- [ ] Tests pass.
- [ ] New behavior has tests.
- [ ] Safety policy still holds.
- [ ] CLI output remains understandable.
- [ ] Documentation updated when user-facing behavior changes.
