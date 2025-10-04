#!/usr/bin/env bash
set -euo pipefail

# --------------------------------------------------------------
# 01-installer.sh — Instalador básico Btrfs + Snapper (Arch Linux)
# Autor: danteRub & GPT-5
# --------------------------------------------------------------
# Este script detecta discos, permite elegir dónde instalar,
# prepara particiones (EFI + Root), crea subvolúmenes y deja
# todo montado en /mnt para continuar con 02-pacstrap.sh
# --------------------------------------------------------------

SUDO=sudo

# --- Dependencias necesarias ---
ensure_dep() {
    if ! command -v "$1" &>/dev/null; then
        echo "Instalando dependencia: $1"
        $SUDO pacman -Sy --noconfirm "$1"
    fi
}

ensure_dep gum
ensure_dep lsblk
ensure_dep parted
ensure_dep sgdisk
ensure_dep btrfs-progs

clear
echo "======================================"
echo "   Instalador Arch Btrfs + Snapper"
echo "======================================"
echo

# --- Detección de discos ---
discos=$(lsblk -dno NAME,SIZE | awk '{print "/dev/"$1" ("$2")"}')

if [[ -z "$discos" ]]; then
    echo "No se detectaron discos disponibles."
    exit 1
fi

echo "Selecciona el disco donde quieres instalar:"
disco=$(echo "$discos" | gum choose)
disco_dev=$(echo "$disco" | awk '{print $1}')
echo "Has elegido $disco_dev"
echo

# --- Detectar particiones existentes ---
particiones=$(lsblk -lno NAME,SIZE,TYPE | awk -v d="$disco_dev" '$3=="part" && $1 ~ substr(d,6) {print "/dev/"$1" ("$2")"}')

if [[ -n "$particiones" ]]; then
    opcion=$(gum choose "Borrar todo el disco" "Instalar en una partición existente")
    if [[ "$opcion" == "Borrar todo el disco" ]]; then
        borrar_todo="yes"
    else
        borrar_todo="no"
    fi
else
    echo "El disco no tiene particiones. Se realizará una instalación limpia."
    borrar_todo="yes"
fi

echo

# --- Inicio del proceso ---
if [[ "$borrar_todo" == "yes" ]]; then
    echo "Detectando modo de arranque..."
    if [[ -d /sys/firmware/efi ]]; then
        modo="UEFI"
    else
        modo="BIOS"
    fi
    echo "Modo detectado: $modo"

    echo "Limpiando disco y creando tabla GPT..."
    $SUDO wipefs -a "$disco_dev" || true
    $SUDO sgdisk --zap-all "$disco_dev" || true
    $SUDO sgdisk -o "$disco_dev"

    if [[ "$modo" == "UEFI" ]]; then
        echo "Creando partición EFI (512 MiB) y raíz Btrfs..."
        $SUDO sgdisk -n 1:1MiB:+512MiB -t 1:ef00 -c 1:"EFI" "$disco_dev"
        $SUDO sgdisk -n 2:0:0 -t 2:8300 -c 2:"Linux_BTRFS" "$disco_dev"
    else
        echo "Creando partición raíz Btrfs (modo BIOS)..."
        $SUDO sgdisk -n 1:1MiB:0 -t 1:8300 -c 1:"Linux_BTRFS" "$disco_dev"
    fi

    $SUDO partprobe "$disco_dev"; $SUDO udevadm settle; sleep 1

    base="$(basename "$disco_dev")"
    if [[ "$base" =~ ^(nvme|mmcblk) ]]; then
        efi_part="${disco_dev}p1"
        root_part="${disco_dev}p2"
    else
        efi_part="${disco_dev}1"
        root_part="${disco_dev}2"
    fi
    [[ "$modo" == "BIOS" ]] && { root_part="${disco_dev}1"; efi_part=""; }

    echo "Formateando particiones..."
    [[ "$modo" == "UEFI" ]] && $SUDO mkfs.fat -F32 -n EFI "$efi_part"
    $SUDO mkfs.btrfs -f -L ArchRoot "$root_part"

    echo "Montando particiones..."
    $SUDO mount "$root_part" /mnt
    [[ "$modo" == "UEFI" ]] && { $SUDO mkdir -p /mnt/boot; $SUDO mount "$efi_part" /mnt/boot; }

else
    # --- USAR PARTICIÓN EXISTENTE ---
    echo "Selecciona la partición donde instalar:"
    part_line="$(echo "$particiones" | gum choose)"
    part_dev="$(awk '{print $1}' <<<"$part_line")"

    # Detectar disco padre
    parent_disk="$(lsblk -no PKNAME "$part_dev" | head -n1)"
    [[ -z "$parent_disk" ]] && parent_disk="$(basename "$part_dev")"
    parent_dev="/dev/$parent_disk"

    echo "Buscando partición EFI existente en $parent_dev..."
    efi_existente="$(lsblk -prno NAME,FSTYPE,PARTTYPE "$parent_dev" \
        | awk '$2~/vfat|fat32/ || $3=="ef00"{print $1; exit}')"

    if [[ -n "$efi_existente" ]]; then
        echo "Se encontró partición EFI existente: $efi_existente"
        echo "Reutilizando sin formatear (posiblemente de Windows)."
        efi_part="$efi_existente"
    else
        echo "No se encontró partición EFI. Creando una nueva (512 MiB)..."
        $SUDO sgdisk -n 1:1MiB:+512MiB -t 1:ef00 -c 1:"EFI" "$parent_dev"
        $SUDO partprobe "$parent_dev"; $SUDO udevadm settle; sleep 1
        if [[ "$parent_dev" =~ ^/dev/nvme ]]; then
            efi_part="${parent_dev}p1"
        else
            efi_part="${parent_dev}1"
        fi
        $SUDO mkfs.fat -F32 -n EFI "$efi_part"
    fi

    echo "Formateando partición raíz ($part_dev)..."
    $SUDO mkfs.btrfs -f -L ArchRoot "$part_dev"

    echo "Montando particiones..."
    $SUDO mount "$part_dev" /mnt
    $SUDO mkdir -p /mnt/boot
    $SUDO mount "$efi_part" /mnt/boot
    root_part="$part_dev"
fi

# --- Crear subvolúmenes y re-montar ---
echo "Creando subvolúmenes Btrfs..."
for sv in @ @home @log @pkg @snapshots; do
    $SUDO btrfs subvolume create "/mnt/$sv"
done

echo "Re-montando con subvolúmenes..."
$SUDO umount -R /mnt
$SUDO mount -o subvol=@,compress=zstd,noatime "$root_part" /mnt
$SUDO mkdir -p /mnt/{home,var/log,var/cache/pacman/pkg,.snapshots,boot}
$SUDO mount -o subvol=@home,compress=zstd,noatime "$root_part" /mnt/home
$SUDO mount -o subvol=@log,compress=zstd,noatime "$root_part" /mnt/var/log
$SUDO mount -o subvol=@pkg,compress=zstd,noatime "$root_part" /mnt/var/cache/pacman/pkg
$SUDO mount -o subvol=@snapshots,compress=zstd,noatime "$root_part" /mnt/.snapshots
[[ -n "${efi_part:-}" ]] && $SUDO mount "$efi_part" /mnt/boot

echo
echo "======================================"
echo "Particionado completo:"
[[ -n "${efi_part:-}" ]] && echo "  EFI:  $efi_part"
echo "  Root: $root_part"
echo "--------------------------------------"
echo "Sistema de archivos preparado y montado en /mnt"
echo "Puedes continuar con ./02-pacstrap.sh"
echo "======================================"
