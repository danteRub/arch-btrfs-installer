#!/usr/bin/env bash
set -euo pipefail

# Instalación limpia en partición Btrfs con Snapper
# Arch Linux + gum

# --- Dependencias ---
ensure_dep() {
    if ! command -v "$1" &>/dev/null; then
        echo "⚠️  Dependencia '$1' no encontrada. Instalando..."
        sudo pacman -Sy --noconfirm "$1"
    fi
}
ensure_dep gum
ensure_dep lsblk
ensure_dep mkfs.btrfs
ensure_dep btrfs
ensure_dep snapper
ensure_dep parted

# --- Funciones para crear particiones ---
crear_particion() {
    local disco="$1"
    local tipo_particion="$2"
    local tamaño="$3"
    
    echo "🔧 Creando tabla de particiones $tipo_particion en $disco..."
    
    if [[ "$tipo_particion" == "GPT" ]]; then
        sudo parted "$disco" mklabel gpt
        if [[ "$tamaño" == "100%" ]]; then
            sudo parted "$disco" mkpart primary btrfs 1MiB 100%
        else
            sudo parted "$disco" mkpart primary btrfs 1MiB "${tamaño}GB"
        fi
    else
        sudo parted "$disco" mklabel msdos
        if [[ "$tamaño" == "100%" ]]; then
            sudo parted "$disco" mkpart primary btrfs 1MiB 100%
        else
            sudo parted "$disco" mkpart primary btrfs 1MiB "${tamaño}GB"
        fi
    fi
    
    # Asegurar que los cambios se escriban
    sudo partprobe "$disco"
    sleep 2
    
    echo "✅ Partición creada en $disco"
}

# --- Selección de disco ---
discos=$(lsblk -dno NAME,SIZE | awk '{print "/dev/"$1" ("$2")"}')

if [[ -z "$discos" ]]; then
    echo "❌ No se detectaron discos."
    exit 1
fi

echo "Selecciona el disco donde quieres instalar:"
disco=$(echo "$discos" | gum choose)
disco_dev=$(echo "$disco" | awk '{print $1}')

# --- Selección de partición ---
particiones=$(lsblk -lno NAME,SIZE,TYPE | awk -v d="$disco_dev" '$3=="part" && $1 ~ substr(d,6) {print "/dev/"$1" ("$2")"}')

if [[ -z "$particiones" ]]; then
    echo "⚠️  El disco $disco_dev no tiene particiones."
    if gum confirm "¿Quieres crear una partición en $disco_dev?"; then
        echo "Selecciona el tipo de tabla de particiones:"
        opciones_tipo=("GPT" "MBR")
        tipo_particion=$(printf '%s\n' "${opciones_tipo[@]}" | gum choose)
        
        echo "Selecciona el tamaño de la partición:"
        opciones_tamaño=("100%" "50GB" "100GB" "200GB" "500GB")
        tamaño=$(printf '%s\n' "${opciones_tamaño[@]}" | gum choose)
        
        if gum confirm "⚠️  Esto BORRARÁ todos los datos en $disco_dev. ¿Continuar?"; then
            crear_particion "$disco_dev" "$tipo_particion" "$tamaño"
            
            # Buscar la nueva partición creada
            sleep 3
            particiones=$(lsblk -lno NAME,SIZE,TYPE | awk -v d="$disco_dev" '$3=="part" && $1 ~ substr(d,6) {print "/dev/"$1" ("$2")"}')
            if [[ -z "$particiones" ]]; then
                echo "❌ Error: No se pudo crear la partición."
                exit 1
            fi
        else
            echo "❎ Cancelado."
            exit 1
        fi
    else
        echo "❎ Cancelado."
        exit 1
    fi
fi

echo "Selecciona la partición del disco $disco_dev para instalar:"
part=$(echo "$particiones" | gum choose)
part_dev=$(echo "$part" | awk '{print $1}')

# --- Plan de acción ---
echo
echo "=== PLAN DE INSTALACIÓN LIMPIA ==="
echo "Disco: $disco_dev"
echo "Partición: $part_dev"
echo
echo "1. Formatear $part_dev como Btrfs (mkfs.btrfs -f -L ArchRoot)."
echo "2. Montar en /mnt."
echo "3. Crear subvolúmenes:"
echo "   @, @home, @log, @pkg, @snapshots"
echo "4. Re-montar con subvolúmenes en:"
echo "   /mnt            -> @"
echo "   /mnt/home       -> @home"
echo "   /mnt/var/log    -> @log"
echo "   /mnt/var/cache/pacman/pkg -> @pkg"
echo "   /mnt/.snapshots -> @snapshots"
echo "5. Configurar Snapper en / y /home."
echo

# --- Confirmación ---
if gum confirm "⚠️  Esto BORRARÁ todo el contenido de $part_dev. ¿Continuar?"; then
    echo "⏳ Ejecutando instalación limpia en $part_dev..."

    # Formatear limpio
    sudo mkfs.btrfs -f -L ArchRoot "$part_dev"

    # Montar raíz temporal
    sudo mount "$part_dev" /mnt

    # Crear subvolúmenes
    for sv in @ @home @log @pkg @snapshots; do
        sudo btrfs subvolume create /mnt/$sv
    done

    # Re-montar con opciones
    sudo umount /mnt
    sudo mount -o subvol=@,compress=zstd,noatime "$part_dev" /mnt
    sudo mkdir -p /mnt/{home,var/log,var/cache/pacman/pkg,.snapshots}
    sudo mount -o subvol=@home,compress=zstd,noatime "$part_dev" /mnt/home
    sudo mount -o subvol=@log,compress=zstd,noatime "$part_dev" /mnt/var/log
    sudo mount -o subvol=@pkg,compress=zstd,noatime "$part_dev" /mnt/var/cache/pacman/pkg
    sudo mount -o subvol=@snapshots,compress=zstd,noatime "$part_dev" /mnt/.snapshots

    # Configuración de Snapper
    sudo arch-chroot /mnt bash -c "
      snapper -c root create-config /
      snapper -c home create-config /home
    "

    echo "✅ Instalación completada en $part_dev (Btrfs + Snapper)"
else
    echo "❎ Cancelado. No se hicieron cambios."
fi
