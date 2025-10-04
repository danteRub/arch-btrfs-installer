#!/usr/bin/env bash
# 01-installer.sh
# Instalación limpia en Btrfs con subvolúmenes + Snapper opcional
# Ahora con lógica para elegir entre formatear todo el disco o usar una partición existente.

set -euo pipefail
[[ -n "${DEBUG:-}" ]] && set -x

SUDO=""
if [[ $EUID -ne 0 ]]; then SUDO="sudo"; fi

# --- Dependencias ---
pkg_for_cmd() {
  case "$1" in
    gum) echo "gum" ;;
    lsblk|blockdev|wipefs|findmnt) echo "util-linux" ;;
    parted|partprobe) echo "parted" ;;
    sgdisk) echo "gdisk" ;;
    mkfs.btrfs|btrfs) echo "btrfs-progs" ;;
    snapper) echo "snapper" ;;
    udevadm) echo "systemd" ;;
    lsof) echo "lsof" ;;
    *) echo "" ;;
  esac
}

ensure_dep() {
  local cmd="$1" pkg
  if ! command -v "$cmd" &>/dev/null; then
    pkg="$(pkg_for_cmd "$cmd")"
    [[ -z "$pkg" ]] && { echo "Error: paquete desconocido para '$cmd'"; exit 1; }
    $SUDO pacman -Sy --noconfirm --needed "$pkg"
  fi
}

for c in gum lsblk findmnt parted sgdisk mkfs.btrfs btrfs snapper partprobe blockdev lsof wipefs udevadm; do
  ensure_dep "$c"
done

# --- Funciones auxiliares ---
first_part_node() {
  local disk="$1" base; base="$(basename "$disk")"
  case "$base" in
    nvme*|mmcblk*|md*) echo "${disk}p1" ;;
    *)                  echo "${disk}1" ;;
  esac
}

wait_for_part() {
  local disk="$1" node timeout=30
  node="$(first_part_node "$disk")"
  for _ in $(seq 1 $timeout); do
    [[ -b "$node" ]] && { echo "$node"; return 0; }
    $SUDO udevadm settle || true
    $SUDO partprobe "$disk" || true
    sleep 0.5
  done
  return 1
}

is_boot_medium_disk() {
  local disk="$1" src bootdisk
  src="$(findmnt -n -o SOURCE /run/archiso/bootmnt 2>/dev/null || true)"
  [[ -z "$src" ]] && return 1
  bootdisk="$(lsblk -no PKNAME "$src" 2>/dev/null || basename "$src")"
  [[ "$bootdisk" == "$(basename "$disk")" ]]
}

# --- Selección de disco ---
discos_raw="$(
  lsblk -dpnr -o NAME,SIZE,MODEL,RO,TYPE,FSTYPE |
  awk '$5=="disk"{print $1"|" $2"|" $3"|" $4"|" $6}'
)"
discos=""
while IFS='|' read -r name size model ro fstype; do
  [[ -z "$name" ]] && continue
  [[ "$ro" == "1" ]] && continue
  [[ "$fstype" =~ ^(iso9660|udf)$ ]] && continue
  if is_boot_medium_disk "$name"; then
    continue
  fi
  discos+="$name ($size) $model"$'\n'
done <<< "$discos_raw"

[[ -z "$discos" ]] && { echo "No hay discos elegibles."; exit 1; }

echo "Selecciona el disco donde instalar Arch Linux:"
disco_line="$(echo "$discos" | sed '/^$/d' | gum choose)"
disco_dev="$(awk '{print $1}' <<<"$disco_line")"
disco_base="$(basename "$disco_dev")"

# --- Detectar particiones existentes ---
particiones="$(
  lsblk -prno NAME,SIZE,TYPE,PKNAME |
  awk -v pk="$disco_base" '$3=="part" && $4==pk {print $1" ("$2")"}'
)"

if [[ -z "$particiones" ]]; then
  echo "El disco $disco_dev no tiene particiones. Se borrará y se creará una nueva."
  borrar_todo="yes"
else
  echo "El disco $disco_dev tiene las siguientes particiones:"
  echo "$particiones"
  modo="$(gum choose "Borrar todo el disco (formateo completo)" "Usar una partición existente" "Cancelar")"
  case "$modo" in
    "Borrar todo el disco"*) borrar_todo="yes" ;;
    "Usar una partición existente") borrar_todo="no" ;;
    *) echo "Cancelado."; exit 0 ;;
  esac
fi

# --- Si se borra todo el disco ---
if [[ "$borrar_todo" == "yes" ]]; then
  echo "Creando nueva tabla GPT y partición única Btrfs..."
  $SUDO wipefs -a "$disco_dev" || true
  $SUDO sgdisk --zap-all "$disco_dev" || true
  $SUDO sgdisk -o "$disco_dev"
  $SUDO sgdisk -n 1:1MiB:0 -t 1:8300 -c 1:"Linux_BTRFS" "$disco_dev"

  $SUDO partprobe "$disco_dev" || true
  $SUDO udevadm settle || true
  sleep 1

  part_dev="$(wait_for_part "$disco_dev")" || {
    echo "Error: no se detectó la nueva partición."
    exit 1
  }
  echo "Partición creada: $part_dev"
else
  echo "Selecciona la partición donde instalar:"
  part_line="$(echo "$particiones" | gum choose)"
  part_dev="$(awk '{print $1}' <<<"$part_line")"
fi

# --- Verificaciones ---
if lsblk -prno MOUNTPOINT "$part_dev" | grep -q "/"; then
  echo "La partición $part_dev está montada. Desmóntala antes de continuar."
  exit 1
fi
if $SUDO lsof "$part_dev" &>/dev/null; then
  echo "Algún proceso está usando $part_dev. Cierre procesos o desactive mapeos antes de continuar."
  exit 1
fi

# --- Confirmación ---
echo
echo "=== PLAN DE INSTALACIÓN ==="
echo "Disco:     $disco_dev"
echo "Partición: $part_dev"
echo
echo "1) Formatear la partición en Btrfs (-L ArchRoot)"
echo "2) Montar en /mnt"
echo "3) Crear subvolúmenes: @, @home, @log, @pkg, @snapshots"
echo "4) Re-montar con opciones y puntos de montaje"
echo "5) Configuración Snapper opcional"
echo

if ! gum confirm "Esto borrará todos los datos en $part_dev. ¿Continuar?"; then
  echo "Cancelado."
  exit 0
fi

# --- Formateo y configuración Btrfs ---
$SUDO mkfs.btrfs -f -L ArchRoot "$part_dev"

$SUDO mount "$part_dev" /mnt
for sv in @ @home @log @pkg @snapshots; do
  $SUDO btrfs subvolume create "/mnt/$sv"
done

$SUDO umount /mnt
$SUDO mount -o subvol=@,compress=zstd,noatime "$part_dev" /mnt
$SUDO mkdir -p /mnt/{home,var/log,var/cache/pacman/pkg,.snapshots}
$SUDO mount -o subvol=@home,compress=zstd,noatime "$part_dev" /mnt/home
$SUDO mount -o subvol=@log,compress=zstd,noatime "$part_dev" /mnt/var/log
$SUDO mount -o subvol=@pkg,compress=zstd,noatime "$part_dev" /mnt/var/cache/pacman/pkg
$SUDO mount -o subvol=@snapshots,compress=zstd,noatime "$part_dev" /mnt/.snapshots

echo
echo "Sistema de archivos preparado y montado:"
findmnt -R /mnt
echo
echo "Ya puedes continuar con la instalación base ejecutando:"
echo "  ./02-pacstrap.sh"
echo
