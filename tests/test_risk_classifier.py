from ai_advisor import CommandRisk, classify_command


def test_read_only_commands_are_safe() -> None:
    safe_commands = [
        "lsblk --json -O",
        "lscpu --json",
        "lspci -nn",
        "findmnt --json",
        "ip link show",
        "timedatectl",
        "efibootmgr -v",
        "uname -a",
    ]

    for command in safe_commands:
        result = classify_command(command)
        assert result.risk == CommandRisk.SAFE
        assert result.requires_confirmation is False


def test_destructive_disk_commands_are_critical() -> None:
    critical_commands = [
        "sudo wipefs -a /dev/nvme0n1",
        "sudo sgdisk --zap-all /dev/sda",
        "parted -s /dev/sda mkpart ESP fat32 1MiB 513MiB",
        "mkfs.btrfs -f -L ArchRoot /dev/nvme0n1p2",
        "mkfs.fat -F32 -n EFI /dev/sda1",
        "bootctl install",
        "grub-install --target=i386-pc /dev/sda",
        "dd if=arch.iso of=/dev/sdb bs=4M status=progress",
    ]

    for command in critical_commands:
        result = classify_command(command)
        assert result.risk == CommandRisk.CRITICAL
        assert result.requires_confirmation is True


def test_installation_state_commands_are_high_risk() -> None:
    high_risk_commands = [
        "pacstrap -K /mnt base linux linux-firmware",
        "pacman -S networkmanager",
        "mount /dev/nvme0n1p2 /mnt",
        "umount -R /mnt",
        "arch-chroot /mnt bash",
        "systemctl enable NetworkManager",
        "genfstab -U /mnt",
    ]

    for command in high_risk_commands:
        result = classify_command(command)
        assert result.risk == CommandRisk.HIGH
        assert result.requires_confirmation is True


def test_unknown_commands_are_not_marked_safe() -> None:
    result = classify_command("custom-installer-action --do-something")

    assert result.risk == CommandRisk.MEDIUM
    assert result.requires_confirmation is False
    assert "Unknown command pattern" in result.reason


def test_empty_command_is_not_safe() -> None:
    result = classify_command("   ")

    assert result.risk == CommandRisk.MEDIUM
    assert result.requires_confirmation is False
