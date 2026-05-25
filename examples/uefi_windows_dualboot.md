# Arch Btrfs AI Advisor

## Summary
UEFI installation plan using Btrfs with systemd-boot; microcode recommendation: intel-ucode.

## Assumptions
- Boot mode detected as UEFI.
- CPU vendor detected as GenuineIntel; microcode: intel-ucode.
- Recommended bootloader path: systemd-boot.

## Warnings
- Windows or NTFS markers were detected; avoid wiping disks without review.
- Possible Windows dual-boot detected. Do not wipe any disk until the target disk and EFI partition have been manually verified.

## Steps
1. Collect system diagnostics
   Generate a read-only diagnostic report before planning installation.
   - Command: `./scripts/diagnostics.sh`
   - Risk: [safe] safe (no confirmation required)
   - Reason: Command is expected to be read-only.

2. Review block devices
   Inspect disks, partitions, filesystems and existing operating system markers.
   - Command: `lsblk --json -O`
   - Risk: [safe] safe (no confirmation required)
   - Reason: Command is expected to be read-only.

3. Verify EFI system partition
   Confirm whether an existing ESP should be reused or a new one must be created.
   - Command: `efibootmgr -v`
   - Risk: [safe] safe (no confirmation required)
   - Reason: Command is expected to be read-only.

4. Run partitioning script only after manual confirmation
   This script may wipe, partition and format storage. Review selected disk and mode before continuing.
   - Command: `./01-installer.sh`
   - Risk: [critical] critical (requires confirmation)
   - Reason: Command may destroy data, modify partitions or alter boot records.

5. Install base system after /mnt is mounted
   Run pacstrap and system configuration only after the target Btrfs layout is mounted under /mnt.
   - Command: `./02-pacstrap.sh`
   - Risk: [high] high (requires confirmation)
   - Reason: Command changes installation state, mounts filesystems or modifies the target system.
