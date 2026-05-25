# Security Policy

This project works around Linux installation, partitioning, filesystems and bootloader configuration. Incorrect use can permanently destroy data.

## Supported branch

Security-related fixes should target the default branch:

```text
main
```

## Reporting a vulnerability

Open a GitHub issue if the problem can be discussed publicly without exposing sensitive details.

Examples of valid security or safety reports:

- a destructive command classified below `critical`,
- a command that modifies the system classified as `safe`,
- an LLM path that bypasses deterministic validation,
- a warning about Windows, NTFS, EFI or multiple disks being hidden,
- diagnostic code that writes outside the intended output file,
- installer code that performs destructive operations without explicit review.

Do not include private machine identifiers, real disk serials, access tokens or secrets in reports.

## Safety expectations

The advisor layer must preserve these rules:

- AI may explain, inspect, classify and recommend.
- AI must not automatically execute destructive commands.
- AI must not choose a disk to wipe without explicit user confirmation.
- Unknown commands must not be classified as `safe`.
- Critical commands must remain critical.
- LLM output must not override deterministic risk labels.

## Critical operations

These operations must be treated as `critical` or equivalent:

```text
wipefs
sgdisk
parted mkpart/rm/resizepart/set
mkfs.*
bootctl install
grub-install
dd ... of=/dev/...
./01-installer.sh
```

## Scope

This project does not provide production support, warranty or guarantees. Treat it as an engineering example and review every command before using it on real hardware.
