#!/usr/bin/env bash
# shellcheck disable=SC2086
[[ -n "${DEBUG:-}" ]] && set -x
set -euo pipefail

# Instalación limpia en partición Btrfs con subvolúmenes + Snapper opcional
# Versión que deja las particiones montadas al finalizar (lista para pacstrap)

SUDO=""
if [[ $EUID -ne 0 ]]; then SUDO="sudo"; fi

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

# --- helpers ---
parent_disk_of() {
  local node="$1" base pk cur
  base="$(basename "$node")"
  cur="$base"
  while :; do
    pk="$(lsblk -no PKNAME "/dev/$cur" 2>/dev/null || true)"
    [[ -z "$pk" ]] && { echo "/dev/$cur"; return 0; }
    cur="$pk"
  done
}

first_part_node() {
  local disk="$1" base; base="$(basename "$disk")"
  case "$base" in
    nvme*|mmcblk*|md*) echo "${disk}p1" ;;
    *)                  echo "${disk}1"  ;;
  esac
}

wait_for_part() {
  local disk="$1" node timeout=40
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
  bootdisk="$(parent_disk_of "$src")"
  [[ "$bootdisk" == "$disk" ]]
}

# --- listar discos elegibles ---
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

[[ -z "$discos" ]] && { echo "No hay discos elegibles (todos son ISO/UDF o el medio de arranque)."; exit 1; }

echo "Selecciona el disco:"
disco_line="$(echo "$discos" | sed '/^$/d' | gum choose)"
disco_dev="$(awk '{print $1}' <<<"$disco_line")"
disco_base="$(basename "$disco_dev")"

# --- crear o usar partición ---
particiones="$(
  lsblk -prno NAME,SIZE,TYPE,PKNAME |
  awk -v pk="$disco_base" '$3=="part" && $4==pk {print $1" ("$2")"}'
)"

if [[ -z "$particiones" ]]; then
  echo "El disco $disco_dev no tiene particiones."
  if gum confirm "¿Crear una nueva partición en $disco_dev? Esto borrará el disco completo."; then
    echo "Selecciona tamaño de la partición:"
    tam_choice="$(gum choose "all" "50GB" "100GB" "200GB" "500GB")"

    echo "Limpiando metadatos previos..."
    $SUDO wipefs -a "$disco_dev" || true
    $SUDO sgdisk --zap-all "$disco_dev" || true

    echo "Creando tabla GPT y partición (tipo 8300)..."
    if [[ "$tam_choice" == "all" ]]; then
      $SUDO sgdisk -o "$disco_dev"
      $SUDO sgdisk -n 1:1MiB:0 -t 1:8300 -c 1:"Linux_BTRFS" "$disco_dev"
    else
      $SUDO parted -s "$disco_dev" mklabel gpt
      $SUDO parted -s "$disco_dev" mkpart primary btrfs 1MiB "$tam_choice"
      $SUDO sgdisk -t 1:8300 -c 1:"Linux_BTRFS" "$disco_dev"
    fi

    $SUDO partprobe "$disco_dev" || true
    $SUDO udevadm settle || true
    sleep 0.5

    nodo_part="$(wait_for_part "$disco_dev")" || {
      echo "Error: el kernel no expuso la partición a tiempo."
      exit 1
    }
    size_part="$(lsblk -nprno SIZE "$nodo_part")"
    particiones="$nodo_part ($size_part)"
  else
    echo "Cancelado."
    exit 0
  fi
fi

echo "Selecciona la partición del disco $disco_dev donde instalar:"
part_line="$(echo "$particiones" | gum choose)"
part_dev="$(awk '{print $1}' <<<"$part_line")"

# --- verificaciones ---
if lsblk -prno MOUNTPOINT "$part_dev" | grep -q "/"; then
  echo "La partición $part_dev está montada. Desmóntala antes de continuar."
  exit 1
fi
if $SUDO lsof "$part_dev" &>/dev/null; then
  echo "Algún proceso está usando $part_dev. Cierre procesos o desactive mapeos antes de continuar."
  exit 1
fi

echo
echo "=== PLAN DE INSTALACIÓN LIMPIA ==="
echo "Disco:     $disco_dev"
echo "Partición: $part_dev"
echo
echo "1) Formatear la partición en Btrfs (-L ArchRoot)"
echo "2) Montar en /mnt"
echo "3) Crear subvolúmenes: @, @home, @log, @pkg, @snapshots"
echo "4) Re-montar con opciones y puntos de montaje"
echo "5) (Opcional) Configurar Snapper dentro del chroot si existe"
echo

if gum confirm "Esto borrará todo el contenido de $part_dev. ¿Continuar y ejecutar?"; then
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
  echo "Ya puedes continuar con la instalación:"
  echo "  pacstrap -K /mnt base linux linux-firmware btrfs-progs"
  echo "  genfstab -U /mnt >> /mnt/etc/fstab"
  echo "  arch-chroot /mnt"
  echo
  echo "Dentro del chroot puedes instalar y configurar Snapper:"
  echo "  pacman -S --needed snapper"
  echo "  snapper -c root create-config /"
  echo "  snapper -c home create-config /home"
  echo
  echo "Las particiones permanecen montadas. Puedes seguir desde aquí."
else
  echo "Cancelado. No se hicieron cambios."
fi
