#!/usr/bin/env bash
set -euo pipefail

# --------------------------------------------------------------
# 02-pacstrap.sh — Instalación base + Bootloader (Arch Linux)
# Autor: danteRub & GPT-5
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

clear
echo "======================================"
echo "   Instalación base de Arch Linux"
echo "======================================"
echo

# --- Confirmar que /mnt está montado ---
if ! mountpoint -q /mnt; then
    echo "Error: /mnt no está montado. Ejecuta primero 01-installer.sh"
    exit 1
fi

# --- Seleccionar kernel ---
kernel=$(gum choose "linux" "linux-lts" "linux-zen" "linux-hardened")
echo "Usando kernel: $kernel"

# --- Paquetes base ---
BASE_PKGS="base $kernel linux-firmware btrfs-progs networkmanager nano vi sudo"

echo
echo "Instalando sistema base en /mnt..."
$SUDO pacstrap -K /mnt $BASE_PKGS

# --- Generar fstab ---
echo "Generando /etc/fstab..."
$SUDO genfstab -U /mnt >> /mnt/etc/fstab

# --- Configuración básica dentro del chroot ---
echo "Aplicando configuración base dentro del chroot..."
$SUDO arch-chroot /mnt env -i bash -e <<'CHROOT'
set -e

# Configuraciones por defecto
timezone_val="Europe/Madrid"
locales_val="es_ES.UTF-8,en_US.UTF-8"
lang_val="es_ES.UTF-8"
hostname_val="archlinux"
create_user="yes"
user_name="rubrick"

# Zona horaria
ln -sf "/usr/share/zoneinfo/$timezone_val" /etc/localtime
hwclock --systohc

# Locales
cp /etc/locale.gen /etc/locale.gen.bak
while IFS= read -r loc; do
  [ -z "$loc" ] && continue
  sed -i -E "s|^#\s*(${loc})$|\1|" /etc/locale.gen || true
done < <(echo "$locales_val" | tr ',' '\n')
locale-gen
echo "LANG=$lang_val" > /etc/locale.conf

# Hostname y hosts
echo "$hostname_val" > /etc/hostname
cat >/etc/hosts <<EOF
127.0.0.1   localhost
::1         localhost
127.0.1.1   $hostname_val.localdomain $hostname_val
EOF

# Root password
echo "Establece contraseña de root:"
passwd

# Usuario normal
if [ "$create_user" = "yes" ]; then
  useradd -m -G wheel -s /bin/bash "$user_name"
  echo "Establece contraseña para $user_name:"
  passwd "$user_name"
  sed -i 's/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers
fi

# Servicios esenciales
systemctl enable NetworkManager
CHROOT

# --- Detectar EFI existente y configurar bootloader ---
echo
echo "Configurando bootloader..."
if [[ -d /mnt/boot/EFI/Microsoft ]]; then
    echo "Se detectó EFI de Windows. Reutilizándola para Arch Linux."
else
    echo "Creando estructura EFI nueva..."
    $SUDO mkdir -p /mnt/boot/EFI
fi

# Instalar systemd-boot
$SUDO arch-chroot /mnt bootctl install

# Obtener UUID raíz
ROOT_UUID=$(blkid -s UUID -o value $(findmnt -no SOURCE /mnt))

# Crear loader.conf
cat <<EOF | $SUDO tee /mnt/boot/loader/loader.conf >/dev/null
default arch
timeout 3
console-mode auto
editor no
EOF

# Crear entrada Arch principal
cat <<EOF | $SUDO tee /mnt/boot/loader/entries/arch.conf >/dev/null
title   Arch Linux
linux   /vmlinuz-$kernel
initrd  /initramfs-$kernel.img
options root=UUID=$ROOT_UUID rootflags=subvol=@ rw quiet
EOF

# Crear fallback opcional
cat <<EOF | $SUDO tee /mnt/boot/loader/entries/arch-fallback.conf >/dev/null
title   Arch Linux (fallback)
linux   /vmlinuz-$kernel
initrd  /initramfs-$kernel-fallback.img
options root=UUID=$ROOT_UUID rootflags=subvol=@ rw
EOF

# --- Mensaje final ---
echo
echo "======================================"
echo "Sistema base instalado con éxito."
echo "Bootloader configurado con systemd-boot."
echo
echo "Windows Boot Manager se ha conservado intacto."
echo
echo "Puedes ejecutar: arch-chroot /mnt"
echo "Para continuar configurando el sistema (usuarios, paquetes, etc.)"
echo "======================================"
