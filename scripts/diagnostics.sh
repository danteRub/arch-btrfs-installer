#!/usr/bin/env bash
set -euo pipefail

# scripts/diagnostics.sh
# Read-only diagnostic exporter for Arch Linux installation planning.
# The script writes only its output report. It must not partition, format,
# mount, unmount, install packages, modify boot records or alter system config.

OUT_DIR="${OUT_DIR:-diagnostics}"
OUT_FILE="${OUT_FILE:-$OUT_DIR/system_report.json}"

mkdir -p "$OUT_DIR"

have() {
  command -v "$1" >/dev/null 2>&1
}

json_escape() {
  python -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || sed 's/\\/\\\\/g; s/"/\\"/g; s/$/\\n/' | tr -d '\n'
}

capture_text() {
  local cmd="$1"
  if bash -lc "$cmd" >/tmp/arch_diag_capture.$$ 2>/tmp/arch_diag_error.$$; then
    cat /tmp/arch_diag_capture.$$
  else
    printf 'COMMAND_FAILED: %s\n' "$cmd"
    cat /tmp/arch_diag_error.$$ || true
  fi
  rm -f /tmp/arch_diag_capture.$$ /tmp/arch_diag_error.$$
}

capture_json_or_text() {
  local cmd="$1"
  capture_text "$cmd" | json_escape
}

boot_mode="BIOS"
if [[ -d /sys/firmware/efi ]]; then
  boot_mode="UEFI"
fi

cpu_vendor="unknown"
if have lscpu; then
  cpu_vendor="$(lscpu | awk -F: '/Vendor ID/ {gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}')"
  [[ -z "$cpu_vendor" ]] && cpu_vendor="unknown"
fi

has_network="unknown"
if have ip; then
  if ip link show | grep -q "state UP"; then
    has_network="yes"
  else
    has_network="no"
  fi
fi

cat > "$OUT_FILE" <<JSON
{
  "schema_version": "0.1.0",
  "generated_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "safety": {
    "mode": "read_only",
    "writes_performed": ["$OUT_FILE"],
    "destructive_operations": false
  },
  "system": {
    "boot_mode": "$boot_mode",
    "cpu_vendor": "$cpu_vendor",
    "network_link_up_detected": "$has_network"
  },
  "commands": {
    "uname_a": $(capture_json_or_text "uname -a"),
    "lsblk_json": $(capture_json_or_text "lsblk --json -O"),
    "lscpu_json": $(capture_json_or_text "lscpu --json"),
    "lspci": $(capture_json_or_text "lspci -nn"),
    "ip_link": $(capture_json_or_text "ip link show"),
    "timedatectl": $(capture_json_or_text "timedatectl"),
    "findmnt": $(capture_json_or_text "findmnt --json"),
    "efibootmgr": $(capture_json_or_text "efibootmgr -v")
  },
  "ai_advisor_notes": {
    "intended_use": "Generate an installation plan and classify command risk before the user executes anything.",
    "must_not_do": [
      "Do not execute partitioning automatically.",
      "Do not format disks automatically.",
      "Do not overwrite boot entries automatically.",
      "Do not assume a disk is safe to wipe."
    ]
  }
}
JSON

printf 'Diagnostic report written to %s\n' "$OUT_FILE"
