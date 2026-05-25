# Safety Policy

This project deals with Arch Linux installation, partitioning, filesystems and bootloader configuration. These operations can permanently destroy user data when executed incorrectly.

The AI advisor layer must be designed as a **human-in-the-loop advisory system**, not as an autonomous installer.

## Non-negotiable rules

1. The AI advisor must not execute destructive commands automatically.
2. The AI advisor must not choose a disk to wipe without explicit user confirmation.
3. The AI advisor must classify destructive commands as `critical`.
4. The AI advisor must preserve and surface warnings about Windows, NTFS, EFI and multi-disk setups.
5. The AI advisor must prefer uncertainty over false confidence.
6. Unknown command patterns must never be classified as `safe`.

## Command risk classes

| Risk | Meaning | Confirmation |
| --- | --- | --- |
| `safe` | Expected read-only command. | Not required. |
| `medium` | Modifies local files, users or configuration but should not destroy storage. | Context-dependent. |
| `high` | Changes installation state, mounts filesystems, installs packages or modifies target system. | Required. |
| `critical` | Can destroy data, partition disks, format filesystems or change boot records. | Required. |

## Always critical

The following must always be treated as `critical`:

```text
./01-installer.sh
wipefs
sgdisk
parted mkpart/rm/resizepart/set
mkfs.*
bootctl install
grub-install
dd ... of=/dev/...
```

## High-risk operations

The following must generally be treated as `high`:

```text
./02-pacstrap.sh
pacstrap
pacman -S
mount
umount
arch-chroot
systemctl enable/disable/start/stop/restart
genfstab
```

## Read-only diagnostics

The diagnostics script must remain read-only:

```bash
./scripts/diagnostics.sh
```

Allowed behavior:

- read hardware and system state,
- create the diagnostics output directory,
- write `diagnostics/system_report.json`.

Forbidden behavior:

- partitioning,
- formatting,
- mounting or unmounting,
- package installation,
- service changes,
- bootloader writes,
- modifying `/etc`, `/boot`, `/mnt` or user files.

## Dual-boot protection

When any Windows, Microsoft, NTFS or EFI markers are detected, the advisor must warn the user before any partitioning step.

Required warning intent:

```text
Windows or NTFS markers were detected. Do not wipe any disk until the target disk and EFI partition have been manually verified.
```

## Multi-disk protection

When more than one disk candidate is detected, the advisor must require explicit selection before destructive operations.

Required warning intent:

```text
Multiple disk candidates detected; require explicit user selection.
```

## LLM integration boundary

Any future LLM integration must sit behind deterministic safety layers:

```text
SystemReport -> HardwareSummary -> deterministic planner/risk classifier -> optional LLM explanation
```

An LLM may:

- explain the plan,
- improve wording,
- ask clarifying questions,
- suggest additional verification steps,
- summarize risk.

An LLM must not:

- downgrade deterministic risk labels,
- hide warnings,
- execute commands,
- invent device names,
- assume a disk is safe to erase,
- remove human confirmation requirements.

## Test expectations

Every safety rule should have a regression test. At minimum:

- destructive commands are `critical`,
- unknown commands are not `safe`,
- `./01-installer.sh` is `critical`,
- `./02-pacstrap.sh` is `high`,
- Windows/NTFS markers create warnings,
- multiple disks create warnings,
- no network creates a pacstrap warning.
