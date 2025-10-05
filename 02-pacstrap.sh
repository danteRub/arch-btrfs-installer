#!/usr/bin/env bash
set -euo pipefail

# --------------------------------------------------------------
# 02-pacstrap.sh — Instalación base + Bootloader + Snapper + Microcode
# Autor: danteRub & GPT-5
# Conforme a la ArchWiki oficial
# --------------------------------------------------------------

SUDO=sudo

ensure_dep() {
    if ! command -v "$1" &>/dev/null; then
        echo "Instalando dependencia: $1"
        $SUDO pacman -Sy --noconfirm "$1"
    fi
}
ensure_dep pacstrap
ensure_dep genfstab
ensure_dep arch-chroot
ensure_dep gum
ensure_dep lscpu

clear
echo "======================================"
echo "   Instalación base de Arch Linux"
echo "======================================"
echo

if ! mountpoint -q /mnt; then
    echo "Error: /mnt no está montado. Ejecuta primero 01-installer.sh"
    exit 1
fi

# --- Detectar modo de arranque ---
if [[ -d /sys/firmware/efi ]]; then
    modo="UEFI"
else
    modo="BIOS"
fi
echo "Modo de arranque detectado: $modo"
echo

# --- Seleccionar kernel ---
kernel=$(gum choose "linux" "linux-lts" "linux-zen" "linux-hardened")
echo "Usando kernel: $kernel"

# --- Detectar microcode CPU ---
cpu_vendor=$(lscpu | awk -F: '/Vendor ID/ {print $2}' | xargs)
ucode_pkg=""

case "$cpu_vendor" in
  GenuineIntel) ucode_pkg="intel-ucode" ;;
  AuthenticAMD) ucode_pkg="amd-ucode" ;;
esac

if [[ -n "$ucode_pkg" ]]; then
    echo "Detectado procesador $cpu_vendor → se instalará $ucode_pkg"
else
    echo "Advertencia: No se detectó CPU Intel/AMD; se omite microcode."
fi

# --- Paquetes base (según ArchWiki) ---
BASE_PKGS="base $kernel linux-firmware $ucode_pkg btrfs-progs networkmanager micro vi sudo snapper"

echo
echo "Instalando sistema base en /mnt..."
$SUDO pacstrap -K /mnt $BASE_PKGS

echo "Generando /etc/fstab..."
$SUDO genfstab -U /mnt >> /mnt/etc/fstab

# --- Configuración básica dentro del chroot ---
echo "Aplicando configuración base dentro del chroot..."
$SUDO arch-chroot /mnt env -i bash -e <<'CHROOT'
set -e

timezone_val="Europe/Madrid"
locales_val="es_ES.UTF-8,en_US.UTF-8"
lang_val="es_ES.UTF-8"
hostname_val="archlinux"
create_user="yes"
user_name="rubrick"

ln -sf "/usr/share/zoneinfo/$timezone_val" /etc/localtime
hwclock --systohc

cp /etc/locale.gen /etc/locale.gen.bak
while IFS= read -r loc; do
  [ -z "$loc" ] && continue
  sed -i -E "s|^#\s*(${loc})$|\1|" /etc/locale.gen || true
done < <(echo "$locales_val" | tr ',' '\n')
locale-gen
echo "LANG=$lang_val" > /etc/locale.conf

echo "$hostname_val" > /etc/hostname
cat >/etc/hosts <<EOF
127.0.0.1   localhost
::1         localhost
127.0.1.1   $hostname_val.localdomain $hostname_val
EOF

echo "Establece contraseña de root:"
passwd

if [ "$create_user" = "yes" ]; then
  useradd -m -G wheel -s /bin/bash "$user_name"
  echo "Establece contraseña para $user_name:"
  passwd "$user_name"
  sed -i 's/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers
fi

systemctl enable NetworkManager

# --- Configurar Snapper ---
if command -v snapper >/dev/null 2>&1; then
    echo "Configurando Snapper..."
    mkdir -p /.snapshots /home/.snapshots
    snapper -c root create-config /
    snapper -c home create-config /home || true

    sed -i 's/^ALLOW_USERS=""/ALLOW_GROUPS="wheel"/' /etc/snapper/configs/root || true
    sed -i 's/^ALLOW_USERS=""/ALLOW_GROUPS="wheel"/' /etc/snapper/configs/home || true

    systemctl enable snapper-timeline.timer || true
    systemctl enable snapper-cleanup.timer || true
fi

# --- Establecer micro como editor por defecto ---
echo 'export EDITOR=micro' > /etc/profile.d/editor.sh
chmod +x /etc/profile.d/editor.sh
CHROOT

# --- Bootloader (solo UEFI) ---
if [[ "$modo" == "UEFI" ]]; then
    echo
    echo "Configurando systemd-boot..."

    if [[ -d /mnt/boot/EFI/Microsoft ]]; then
        echo "Se detectó EFI de Windows. Reutilizándola."
    else
        echo "Creando estructura EFI nueva..."
        $SUDO mkdir -p /mnt/boot/EFI
    fi

    $SUDO arch-chroot /mnt bootctl install

    ROOT_UUID=$(blkid -s UUID -o value $(findmnt -no SOURCE /mnt))

    cat <<EOF | $SUDO tee /mnt/boot/loader/loader.conf >/dev/null
default arch
timeout 3
console-mode auto
editor no
EOF

    # Entrada principal
    cat <<EOF | $SUDO tee /mnt/boot/loader/entries/arch.conf >/dev/null
title   Arch Linux
linux   /vmlinuz-$kernel
EOF

    if [[ -f /mnt/boot/intel-ucode.img ]]; then
        echo "initrd  /intel-ucode.img" | $SUDO tee -a /mnt/boot/loader/entries/arch.conf >/dev/null
    elif [[ -f /mnt/boot/amd-ucode.img ]]; then
        echo "initrd  /amd-ucode.img" | $SUDO tee -a /mnt/boot/loader/entries/arch.conf >/dev/null
    fi

    cat <<EOF | $SUDO tee -a /mnt/boot/loader/entries/arch.conf >/dev/null
initrd  /initramfs-$kernel.img
options root=UUID=$ROOT_UUID rootflags=subvol=@ rw quiet
EOF

    # Fallback
    cat <<EOF | $SUDO tee /mnt/boot/loader/entries/arch-fallback.conf >/dev/null
title   Arch Linux (fallback)
linux   /vmlinuz-$kernel
EOF

    if [[ -f /mnt/boot/intel-ucode.img ]]; then
        echo "initrd  /intel-ucode.img" | $SUDO tee -a /mnt/boot/loader/entries/arch-fallback.conf >/dev/null
    elif [[ -f /mnt/boot/amd-ucode.img ]]; then
        echo "initrd  /amd-ucode.img" | $SUDO tee -a /mnt/boot/loader/entries/arch-fallback.conf >/dev/null
    fi

    cat <<EOF | $SUDO tee -a /mnt/boot/loader/entries/arch-fallback.conf >/dev/null
initrd  /initramfs-$kernel-fallback.img
options root=UUID=$ROOT_UUID rootflags=subvol=@ rw
EOF

    echo
    echo "Systemd-boot instalado correctamente."
    echo "Windows Boot Manager se ha conservado intacto."
else
    echo
    echo "El sistema está en modo BIOS (Legacy)."
    echo "No se instalará ningún bootloader."
    echo "Puedes instalar GRUB u otro gestor más tarde si lo deseas:"
    echo "  arch-chroot /mnt grub-install --target=i386-pc /dev/sdX"
    echo "  arch-chroot /mnt grub-mkconfig -o /boot/grub/grub.cfg"
fi

echo
echo "======================================"
echo "Sistema base instalado con éxito."
echo "Snapper configurado, microcode aplicado,"
echo "systemd-boot instalado (si UEFI) y micro como editor por defecto."
echo "Puedes reiniciar o continuar en chroot."
echo "======================================"
