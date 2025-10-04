#!/usr/bin/env bash
# 02-pacstrap.sh
# Prepara el sistema base dentro de /mnt y aplica configuración mínima.
# Requisitos: /mnt y subvolúmenes montados; conexión a Internet.

set -euo pipefail

SUDO=""
if [[ $EUID -ne 0 ]]; then SUDO="sudo"; fi

need() { command -v "$1" >/dev/null 2>&1 || { echo "Falta '$1'"; exit 1; }; }

# Dependencias del live
for c in gum pacstrap genfstab arch-chroot lsblk lscpu timedatectl; do
  need "$c"
done

# Comprobaciones previas
[[ -d /mnt ]] || { echo "/mnt no existe"; exit 1; }
mountpoint -q /mnt || { echo "/mnt no está montado"; exit 1; }

echo "Detectando CPU para microcódigo..."
cpu_vendor="$(lscpu | awk -F: '/Vendor ID/{gsub(/^[ \t]+/, "", $2); print $2}')"
ucode_pkg=""
case "$cpu_vendor" in
  GenuineIntel) ucode_pkg="intel-ucode" ;;
  AuthenticAMD) ucode_pkg="amd-ucode" ;;
esac
[[ -n "$ucode_pkg" ]] && echo "Se instalará microcódigo: $ucode_pkg" || echo "No se detectó microcódigo específico."

echo "Selecciona kernel:"
kernel="$(printf "%s\n" "linux" "linux-lts" | gum choose)"

echo "Paquetes base adicionales (mínimos ya incluidos: btrfs-progs, $kernel, linux-firmware):"
# Lista recomendada
recommended=("base" "linux-firmware" "btrfs-progs" "vi" "vim" "nano" "networkmanager" "sudo" "grub" "efibootmgr" "snapper")
# Menú múltiple
selected=$(printf "%s\n" "${recommended[@]}" | gum choose --no-limit)
# Montamos lista final
pkgs=("$kernel" "linux-firmware" "btrfs-progs")
[[ -n "$ucode_pkg" ]] && pkgs+=("$ucode_pkg")
# Añade seleccionados evitando duplicados
for p in $selected; do
  [[ " ${pkgs[*]} " == *" $p "* ]] || pkgs+=("$p")
done
# Garantiza "base"
if [[ " ${pkgs[*]} " != *" base "* ]]; then pkgs=("base" "${pkgs[@]}"); fi

echo "Se instalarán los siguientes paquetes:"
printf ' - %s\n' "${pkgs[@]}"

if gum confirm "¿Continuar con pacstrap?"; then
  $SUDO pacstrap -K /mnt "${pkgs[@]}"
else
  echo "Cancelado."
  exit 0
fi

echo "Generando fstab..."
$SUDO genfstab -U /mnt >> /mnt/etc/fstab

# Parámetros interactivos de sistema
echo "Introduce el hostname del sistema:"
hostname_val="$(gum input --placeholder 'archbox')"
[[ -z "$hostname_val" ]] && hostname_val="archbox"

# Locale y zona horaria por defecto (puedes cambiarlos en las preguntas)
tz_default="Europe/Madrid"
echo "Zona horaria (por defecto $tz_default):"
timezone_val="$(gum input --value "$tz_default")"
[[ -z "$timezone_val" ]] && timezone_val="$tz_default"

echo "Locales a generar (coma-separados, por defecto es_ES.UTF-8,en_US.UTF-8):"
locales_val="$(gum input --value 'es_ES.UTF-8,en_US.UTF-8')"
[[ -z "$locales_val" ]] && locales_val="es_ES.UTF-8,en_US.UTF-8"

lang_default="es_ES.UTF-8"
echo "LANG por defecto ($lang_default):"
lang_val="$(gum input --value "$lang_default")"
[[ -z "$lang_val" ]] && lang_val="$lang_default"

# Usuario opcional
create_user="no"
if gum confirm "¿Crear un usuario administrador además de root?"; then
  create_user="yes"
  echo "Nombre de usuario:"
  user_name="$(gum input --placeholder 'rubrick')"
  [[ -z "$user_name" ]] && { echo "Usuario vacío. Abortando creación de usuario."; create_user="no"; }
fi

echo "Aplicando configuración base dentro del chroot..."
$SUDO arch-chroot /mnt bash -eu <<CHROOT
set -euo pipefail

# Zona horaria y reloj
ln -sf "/usr/share/zoneinfo/$timezone_val" /etc/localtime
hwclock --systohc

# Locales
# Activar líneas en /etc/locale.gen
cp /etc/locale.gen /etc/locale.gen.bak
IFS=',' read -r -a _locs <<< "$locales_val"
for loc in "\${_locs[@]}"; do
  sed -i "s/^#\\s*\\($loc\\)\$/\\1/" /etc/locale.gen || true
done
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
echo "Establece la contraseña de root:"
passwd

# Usuario administrador opcional
if [[ "$create_user" == "yes" ]]; then
  useradd -m -G wheel -s /bin/bash "$user_name"
  echo "Establece la contraseña para $user_name:"
  passwd "$user_name"
  # Habilitar sudo para wheel
  sed -i 's/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers
fi

# Habilitar servicios útiles si están instalados
if command -v systemctl >/dev/null 2>&1; then
  if command -v NetworkManager >/dev/null 2>&1; then
    systemctl enable NetworkManager
  fi
  # Snapper timers básicos si snapper existe
  if command -v snapper >/dev/null 2>&1; then
    # Crear configuraciones para / y /home si existen
    snapper -c root create-config / || true
    if [ -d /home ]; then
      snapper -c home create-config /home || true
    fi
  fi
fi
CHROOT

echo "Configuración base aplicada."

# Recordatorio de bootloader
echo
echo "Siguiente paso: instalar y configurar el cargador de arranque."
echo "Si tienes partición EFI montada en /mnt/boot, puedes usar systemd-boot:"
echo "  arch-chroot /mnt bootctl install"
echo "o si prefieres GRUB (ya instalado si lo elegiste):"
echo "  arch-chroot /mnt grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=Arch"
echo "  arch-chroot /mnt grub-mkconfig -o /boot/grub/grub.cfg"
echo
echo "Sistema base listo. Puedes reiniciar cuando termines el bootloader."