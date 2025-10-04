#!/usr/bin/env bash
set -euo pipefail

# Instalación limpia en partición Btrfs con subvolúmenes + Snapper opcional
# Arch Linux + gum, multi-disco, single-partición

### --- helpers / deps ---
SUDO=""
if [[ $EUID -ne 0 ]]; then
  SUDO="sudo"
fi

pkg_for_cmd() {
  case "$1" in
    gum) echo "gum" ;;
    lsblk) echo "util-linux" ;;
    parted|partprobe) echo "parted" ;;
    mkfs.btrfs|btrfs) echo "btrfs-progs" ;;
    snapper) echo "snapper" ;;
    *) echo "" ;;
  esac
}

ensure_dep() {
  local cmd="$1"
  if ! command -v "$cmd" &>/dev/null; then
    local pkg; pkg="$(pkg_for_cmd "$cmd")"
    if [[ -z "$pkg" ]]; then
      echo "Error: no se puede determinar el paquete para '$cmd'." >&2
      exit 1
    fi
    echo "Instalando dependencia '$cmd' (paquete: $pkg)..."
    $SUDO pacman -Sy --noconfirm --needed "$pkg"
  fi
}

for c in gum lsblk parted mkfs.btrfs btrfs snapper partprobe; do
  ensure_dep "$c"
done

cleanup() {
  set +e
  $SUDO umount -R /mnt &>/dev/null || true
}
trap cleanup EXIT

### --- selección de disco ---
discos="$(
  lsblk -dprno NAME,SIZE,MODEL |
  awk '{print $1" ("$2") "substr($0, index($0,$3))}' |
  sed 's/  */ /g'
)"

[[ -z "$discos" ]] && { echo "No se detectaron discos."; exit 1; }

echo "Selecciona el disco:"
disco_line="$(echo "$discos" | gum choose)"
disco_dev="$(awk '{print $1}' <<<"$disco_line")"
disco_base="$(basename "$disco_dev")"

### --- selección o creación de partición ---
particiones="$(
  lsblk -prno NAME,SIZE,TYPE,PKNAME |
  awk -v pk="$disco_base" '$3=="part" && $4==pk {print $1" ("$2")"}'
)"

if [[ -z "$particiones" ]]; then
  echo "El disco $disco_dev no tiene particiones."
  if gum confirm "¿Quieres crear una nueva partición en $disco_dev? Esto borrará todo el disco."; then
    echo "Selecciona el tipo de tabla de particiones:"
    tipo_tabla="$(gum choose "GPT" "MBR")"

    echo "Selecciona el tamaño de la partición:"
    tam_choice="$(gum choose "all" "50GB" "100GB" "200GB" "500GB")"
    tam_norm="$tam_choice"

    echo "Creando tabla $tipo_tabla y partición en $disco_dev..."
    if [[ "$tipo_tabla" == "GPT" ]]; then
      $SUDO parted -s "$disco_dev" mklabel gpt
    else
      $SUDO parted -s "$disco_dev" mklabel msdos
    fi

    if [[ "$tam_norm" == "all" ]]; then
      $SUDO parted -s "$disco_dev" mkpart primary btrfs 1MiB 100%
    else
      $SUDO parted -s "$disco_dev" mkpart primary btrfs 1MiB "$tam_norm"
    fi

    $SUDO partprobe "$disco_dev"
    sleep 2

    particiones="$(
      lsblk -prno NAME,SIZE,TYPE,PKNAME |
      awk -v pk="$disco_base" '$3=="part" && $4==pk {print $1" ("$2")"}'
    )"
    [[ -z "$particiones" ]] && { echo "Error: no se pudo crear la partición."; exit 1; }
  else
    echo "Cancelado por el usuario."
    exit 0
  fi
fi

echo "Selecciona la partición del disco $disco_dev donde instalar:"
part_line="$(echo "$particiones" | gum choose)"
part_dev="$(awk '{print $1}' <<<"$part_line")"

# No seguir si está montada
if lsblk -prno MOUNTPOINT "$part_dev" | grep -q "/" ; then
  echo "La partición $part_dev está montada. Desmóntala antes de continuar."
  exit 1
fi

### --- plan ---
echo
echo "=== PLAN DE INSTALACIÓN LIMPIA ==="
echo "Disco:      $disco_dev"
echo "Partición:  $part_dev"
echo
echo "1) Formatear $part_dev como Btrfs (mkfs.btrfs -f -L ArchRoot)"
echo "2) Montar en /mnt"
echo "3) Crear subvolúmenes: @, @home, @log, @pkg, @snapshots"
echo "4) Re-montar con opciones:"
echo "   /mnt                       -> @"
echo "   /mnt/home                  -> @home"
echo "   /mnt/var/log               -> @log"
echo "   /mnt/var/cache/pacman/pkg  -> @pkg"
echo "   /mnt/.snapshots            -> @snapshots"
echo "5) (Opcional) Configurar Snapper dentro del chroot"
echo

if gum confirm "Esto borrará todo el contenido de $part_dev. ¿Continuar y ejecutar?"; then
  echo "Formateando $part_dev..."
  $SUDO mkfs.btrfs -f -L ArchRoot "$part_dev"

  echo "Montando y creando subvolúmenes..."
  $SUDO mount "$part_dev" /mnt
  for sv in @ @home @log @pkg @snapshots; do
    $SUDO btrfs subvolume create "/mnt/$sv"
  done

  echo "Re-montando con opciones..."
  $SUDO umount /mnt
  $SUDO mount -o subvol=@,compress=zstd,noatime "$part_dev" /mnt
  $SUDO mkdir -p /mnt/{home,var/log,var/cache/pacman/pkg,.snapshots}
  $SUDO mount -o subvol=@home,compress=zstd,noatime "$part_dev" /mnt/home
  $SUDO mount -o subvol=@log,compress=zstd,noatime "$part_dev" /mnt/var/log
  $SUDO mount -o subvol=@pkg,compress=zstd,noatime "$part_dev" /mnt/var/cache/pacman/pkg
  $SUDO mount -o subvol=@snapshots,compress=zstd,noatime "$part_dev" /mnt/.snapshots

  echo "Recuerda generar fstab tras el pacstrap con:"
  echo "  genfstab -U /mnt >> /mnt/etc/fstab"
  echo

  if [[ -x /mnt/usr/bin/snapper ]]; then
    echo "Configurando Snapper dentro del chroot..."
    $SUDO arch-chroot /mnt bash -eu -c '
      snapper -c root create-config / || true
      snapper -c home create-config /home || true
    '
  else
    echo "Snapper aún no está instalado dentro del sistema."
    echo "Tras el pacstrap, ejecuta dentro del chroot:"
    echo "  pacman -S --needed snapper"
    echo "  snapper -c root create-config /"
    echo "  snapper -c home create-config /home"
  fi

  echo "Instalación completada: partición preparada con Btrfs y subvolúmenes."
else
  echo "Cancelado. No se hicieron cambios."
fi
