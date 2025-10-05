#!/usr/bin/env bash
set -euo pipefail

# 01-installer.sh — Particionado Btrfs + (opcional) ESP, con montaje final listo para pacstrap
# - Desmonta todo lo que esté usando el disco elegido
# - Fuerza relectura de la tabla (partprobe + udevadm + sync + espera)
# - Reutiliza ESP existente; crea una nueva SOLO al borrar disco o si hay espacio libre claro

SUDO=sudo

need() { command -v "$1" >/dev/null 2>&1 || { echo "Instalando $1"; $SUDO pacman -Sy --noconfirm "$1"; }; }
for c in gum lsblk sgdisk parted btrfs-progs findmnt; do need "$c"; done

# Helpers
disk_base() { basename "$1"; }
is_nvme_like() { [[ "$(disk_base "$1")" =~ ^(nvme|mmcblk|md) ]]; }
pnum() { # echo /dev/sda + 1 -> /dev/sda1 ; /dev/nvme0n1 + 1 -> /dev/nvme0n1p1
  local d="$1" n="$2"; if is_nvme_like "$d"; then echo "${d}p${n}"; else echo "${d}${n}"; fi
}
rereadpt() {
  local d="$1"
  sync || true
  $SUDO partprobe "$d" || true
  $SUDO udevadm settle || true
  for _ in {1..12}; do sleep 0.5; done
}
umount_disk_mounts() {
  local d="$1"
  echo "Desmontando cualquier punto de montaje en $d..."
  # desmontar /mnt primero si cuelga de ese disco
  $SUDO umount -R /mnt 2>/dev/null || true
  # desmontar cualquier otro punto que pertenezca al disco/particiones
  mapfile -t mps < <(lsblk -lnpo MOUNTPOINT "$d" 2>/dev/null | sed '/^$/d' | sort -u)
  if ((${#mps[@]})); then
    for mp in "${mps[@]}"; do $SUDO umount -R "$mp" 2>/dev/null || true; done
  fi
}

esp_on_disk() { # devuelve la primera ESP (vfat/ef00) del disco, si existe
  local d="$1"
  lsblk -prno NAME,FSTYPE,PARTTYPE "$d" | awk '$2~/^vfat|fat32$/ || $3=="ef00"{print $1; exit}'
}

find_free_for_esp() { # usa parted para localizar un hueco >= 550MiB
  local d="$1"
  parted -sm "$d" unit MiB print free | awk -F: '$1=="free"{gsub("MiB","",$4); gsub("MiB","",$5); s=$4; e=$5; if (e-s>=550) {print s ":" e; exit} }'
}

# Discos elegibles
discos="$(lsblk -dprno NAME,SIZE,MODEL | awk '{print $1" ("$2") "substr($0, index($0,$3))}')"
[[ -z "$discos" ]] && { echo "No hay discos visibles."; exit 1; }

echo "Selecciona el disco donde quieres instalar:"
disco_line="$(echo "$discos" | gum choose)"
disco_dev="$(awk '{print $1}' <<<"$disco_line")"
echo "Has elegido $disco_dev"
echo

# Desmontar lo que esté en uso sobre el disco
umount_disk_mounts "$disco_dev"

# Detectar particiones
particiones="$(lsblk -prno NAME,SIZE,TYPE,PKNAME | awk -v pk="$(disk_base "$disco_dev")" '$3=="part" && $4==pk {print $1" ("$2")"}')"

# Elegir modo
if [[ -n "$particiones" ]]; then
  modo_op="$(gum choose "Borrar todo el disco (limpio)" "Usar una partición existente" "Cancelar")"
  [[ "$modo_op" == "Cancelar" ]] && { echo "Cancelado."; exit 0; }
  borrar_todo=$([[ "$modo_op" == "Borrar todo el disco (limpio)" ]] && echo yes || echo no)
else
  echo "El disco no tiene particiones. Se realizará instalación limpia."
  borrar_todo=yes
fi

# Detectar UEFI/BIOS
if [[ -d /sys/firmware/efi ]]; then arranque="UEFI"; else arranque="BIOS"; fi
echo "Modo detectado: $arranque"
echo

# Variables de salida
efi_part=""
root_part=""

if [[ "$borrar_todo" == "yes" ]]; then
  echo "Limpiando tabla de particiones y creando GPT nueva..."
  $SUDO wipefs -a "$disco_dev" || true
  $SUDO sgdisk --zap-all "$disco_dev" || true
  $SUDO sgdisk -o "$disco_dev"
  rereadpt "$disco_dev"

  if [[ "$arranque" == "UEFI" ]]; then
    echo "Creando ESP (512MiB) y raíz Btrfs en el resto..."
    $SUDO sgdisk -n 1:1MiB:+512MiB -t 1:ef00 -c 1:"EFI" "$disco_dev"
    $SUDO sgdisk -n 2:0:0       -t 2:8300 -c 2:"Linux_BTRFS" "$disco_dev"
    rereadpt "$disco_dev"
    efi_part="$(pnum "$disco_dev" 1)"
    root_part="$(pnum "$disco_dev" 2)"
  else
    echo "Modo BIOS: creando raíz Btrfs ocupando todo el disco..."
    $SUDO sgdisk -n 1:1MiB:0 -t 1:8300 -c 1:"Linux_BTRFS" "$disco_dev"
    rereadpt "$disco_dev"
    root_part="$(pnum "$disco_dev" 1)"
    efi_part=""
  fi

  echo "Formateando..."
  [[ -n "$efi_part" ]] && $SUDO mkfs.fat -F32 -n EFI "$efi_part"
  $SUDO mkfs.btrfs -f -L ArchRoot "$root_part"

  echo "Montando raíz en /mnt..."
  $SUDO mount "$root_part" /mnt
  if [[ -n "$efi_part" ]]; then
    $SUDO mkdir -p /mnt/boot
    $SUDO mount "$efi_part" /mnt/boot
  fi

else
  # Usar partición existente
  echo "Selecciona la partición donde instalar (se formateará en Btrfs):"
  part_line="$(echo "$particiones" | gum choose)"
  root_part="$(awk '{print $1}' <<<"$part_line")"

  echo "Buscando ESP existente en el mismo disco..."
  parent="/dev/$(lsblk -no PKNAME "$root_part")"
  efi_part="$(esp_on_disk "$parent" || true)"

  if [[ -z "$efi_part" && "$arranque" == "UEFI" ]]; then
    echo "No hay ESP en $parent. Comprobando espacio libre para crear una..."
    free_span="$(find_free_for_esp "$parent" || true)"
    if [[ -n "$free_span" ]]; then
      start="$(cut -d: -f1 <<<"$free_span")MiB"
      end="$(cut -d: -f2 <<<"$free_span")MiB"
      echo "Creando ESP en hueco libre ${start}-${end}..."
      $SUDO parted -s "$parent" mkpart ESP fat32 "$start" "$end"
      # marcarla como ESP
      # determinar índice de la nueva partición (la última)
      newidx="$(lsblk -prno NAME,PKNAME "$parent" | awk -v p="$(disk_base "$parent")" '$2~p{print $1}' | wc -l)"
      $SUDO sgdisk -t "$newidx":ef00 -c "$newidx":"EFI" "$parent"
      rereadpt "$parent"
      efi_part="$(pnum "$parent" "$newidx")"
      $SUDO mkfs.fat -F32 -n EFI "$efi_part"
    else
      echo "No hay espacio libre suficiente para crear ESP. Continuaré sin /mnt/boot."
      echo "Después podrás crearla manualmente o usar GRUB en BIOS/Legacy."
      efi_part=""
    fi
  fi

  echo "Formateando la partición seleccionada como Btrfs..."
  $SUDO mkfs.btrfs -f -L ArchRoot "$root_part"

  echo "Montando..."
  $SUDO mount "$root_part" /mnt
  if [[ -n "$efi_part" ]]; then
    $SUDO mkdir -p /mnt/boot
    $SUDO mount "$efi_part" /mnt/boot
  fi
fi

# Subvolúmenes
echo "Creando subvolúmenes Btrfs..."
for sv in @ @home @log @pkg @snapshots; do
  $SUDO btrfs subvolume create "/mnt/$sv"
done

echo "Re-montando con subvolúmenes..."
$SUDO umount -R /mnt
$SUDO mount -o subvol=@,compress=zstd,noatime "$root_part" /mnt
$SUDO mkdir -p /mnt/{home,var/log,var/cache/pacman/pkg,.snapshots}
$SUDO mount -o subvol=@home,compress=zstd,noatime "$root_part" /mnt/home
$SUDO mount -o subvol=@log,compress=zstd,noatime "$root_part" /mnt/var/log
$SUDO mount -o subvol=@pkg,compress=zstd,noatime "$root_part" /mnt/var/cache/pacman/pkg
$SUDO mount -o subvol=@snapshots,compress=zstd,noatime "$root_part" /mnt/.snapshots
if [[ -n "$efi_part" ]]; then
  $SUDO mkdir -p /mnt/boot
  $SUDO mount "$efi_part" /mnt/boot
fi

echo
echo "=== Resultado ==="
[[ -n "$efi_part" ]] && echo "ESP:  $efi_part (montada en /mnt/boot)"
echo "ROOT: $root_part (montada en /mnt)"
echo
echo "Árbol de montajes actual:"
findmnt -R /mnt || true
echo
echo "Listo. Continúa con:  ./02-pacstrap.sh"
