#!/usr/bin/env bash
#
# Copyright (C) 2022 Ing <https://github.com/wjz304>
#
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#

APP_VAR_DIR="/var/apps/fn-vgmng/var"
LOG_FILE="${APP_VAR_DIR}/vgmng.log"
AUTO_MOUNT_STATE_FILE="${APP_VAR_DIR}/auto-mounts.state"
APP_SHARE_DIR="/var/apps/fn-vgmng/shares"
APP_SHARE_ROOT="${APP_SHARE_DIR}/fn-vgmng"
APP_SHARE_PREFIX="imported-"
LEGACY_APP_NAMES="fn-mdmng"

sanitize_mount_name() {
  local value="$1"

  value=$(printf '%s' "${value}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9._-]/-/g; s/-\{2,\}/-/g; s/^-//; s/-$//')
  if [ -z "${value}" ]; then
    value="imported"
  fi
  printf '%s' "${value}"
}

resolve_mount_root() {
  local resolved

  resolved=$(readlink -f "${APP_SHARE_ROOT}" 2>/dev/null || true)
  if [ -n "${resolved}" ]; then
    printf '%s' "${resolved}"
    return 0
  fi

  printf '%s' "${APP_SHARE_ROOT}"
}

MOUNT_ROOT="$(resolve_mount_root)"

mount_alias_path() {
  local target="$1"

  case "${target}" in
    "${MOUNT_ROOT}")
      printf '%s' "${APP_SHARE_ROOT}"
      ;;
    "${MOUNT_ROOT}"/*)
      printf '%s%s' "${APP_SHARE_ROOT}" "${target#${MOUNT_ROOT}}"
      ;;
    *)
      printf '%s' "${target}"
      ;;
  esac
}

resolve_mount_target() {
  local target="$1"

  case "${target}" in
    "${APP_SHARE_ROOT}")
      printf '%s' "${MOUNT_ROOT}"
      ;;
    "${APP_SHARE_ROOT}"/*)
      printf '%s%s' "${MOUNT_ROOT}" "${target#${APP_SHARE_ROOT}}"
      ;;
    "${MOUNT_ROOT}" | "${MOUNT_ROOT}"/*)
      printf '%s' "${target}"
      ;;
    *)
      return 1
      ;;
  esac
}

legacy_app_share_root() {
  local app_name="$1"

  [ -n "${app_name}" ] || return 1
  printf '/var/apps/%s/shares/%s' "${app_name}" "${app_name}"
}

legacy_mount_root() {
  local app_name="$1"
  local alias_root
  local resolved

  alias_root=$(legacy_app_share_root "${app_name}") || return 1
  resolved=$(readlink -f "${alias_root}" 2>/dev/null || true)
  if [ -n "${resolved}" ]; then
    printf '%s' "${resolved}"
    return 0
  fi

  if [ -d "/vol1/@appshare/${app_name}" ]; then
    printf '/vol1/@appshare/%s' "${app_name}"
    return 0
  fi

  printf '%s' "${alias_root}"
}

is_legacy_mount_target() {
  local target="$1"
  local app_name
  local alias_root
  local real_root

  [ -n "${target}" ] || return 1

  for app_name in ${LEGACY_APP_NAMES}; do
    alias_root=$(legacy_app_share_root "${app_name}") || continue
    real_root=$(legacy_mount_root "${app_name}") || continue
    case "${target}" in
      "${alias_root}" | "${alias_root}"/* | "${real_root}" | "${real_root}"/* | /vol*/@appshare/"${app_name}" | /vol*/@appshare/"${app_name}"/*)
        return 0
        ;;
    esac
  done

  return 1
}

detect_active_mountpoint() {
  local device="$1"
  local target

  [ -n "${device}" ] || return 1

  if command_exists findmnt; then
    target=$(findmnt -rn -S "${device}" -o TARGET 2>/dev/null | head -n 1)
    if [ -n "${target}" ]; then
      printf '%s' "${target}"
      return 0
    fi
  fi

  target=$(detect_mountpoint "${device}")
  if [ -n "${target}" ]; then
    printf '%s' "${target}"
    return 0
  fi

  return 1
}

migrate_managed_mount() {
  local source_target="$1"
  local target="$2"

  [ -n "${source_target}" ] || return 1
  [ -n "${target}" ] || return 1
  [ "${source_target}" != "${target}" ] || return 0

  mkdir -p "${target}" || return 1
  mount --move "${source_target}" "${target}" >>"${LOG_FILE}" 2>&1 || return 1

  case "${source_target}" in
    "${MOUNT_ROOT}"/*)
      rmdir "${source_target}" >/dev/null 2>&1 || true
      ;;
    *)
      if is_legacy_mount_target "${source_target}"; then
        rmdir "${source_target}" >/dev/null 2>&1 || true
      fi
      ;;
  esac

  return 0
}

mkdir -p "${APP_VAR_DIR}" >/dev/null 2>&1 || true

escape_json() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e ':a;N;$!ba;s/\n/\\n/g'
}

log_msg() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >>"${LOG_FILE}"
}

remember_auto_mount() {
  local device="$1"
  local target="$2"
  local mode="${3:-ro}"
  local tmp_file

  [ -n "${device}" ] || return 1
  [ -n "${target}" ] || return 1
  [ "${mode}" = "rw" ] || mode="ro"

  tmp_file=$(mktemp "${APP_VAR_DIR}/auto-mounts.XXXXXX") || return 1
  if [ -f "${AUTO_MOUNT_STATE_FILE}" ]; then
    awk -F'|' -v device="${device}" -v target="${target}" '
      !(NF >= 2 && ($1 == device || $2 == target))
    ' "${AUTO_MOUNT_STATE_FILE}" >"${tmp_file}" 2>/dev/null || true
  fi
  printf '%s|%s|%s\n' "${device}" "${target}" "${mode}" >>"${tmp_file}"
  mv "${tmp_file}" "${AUTO_MOUNT_STATE_FILE}"
}

forget_auto_mount() {
  local device="$1"
  local target="$2"
  local tmp_file

  [ -f "${AUTO_MOUNT_STATE_FILE}" ] || return 0
  [ -n "${device}${target}" ] || return 0

  tmp_file=$(mktemp "${APP_VAR_DIR}/auto-mounts.XXXXXX") || return 1
  awk -F'|' -v device="${device}" -v target="${target}" '
    !(NF >= 2 && ((device != "" && $1 == device) || (target != "" && $2 == target)))
  ' "${AUTO_MOUNT_STATE_FILE}" >"${tmp_file}" 2>/dev/null || true
  mv "${tmp_file}" "${AUTO_MOUNT_STATE_FILE}"
}

list_auto_mounts() {
  [ -f "${AUTO_MOUNT_STATE_FILE}" ] || return 0
  awk -F'|' 'NF >= 3 && $1 != "" && $2 != "" { print $1 "|" $2 "|" $3 }' "${AUTO_MOUNT_STATE_FILE}" 2>/dev/null
}

auto_mounts_json() {
  local first=1
  local device=""
  local target=""
  local mode=""

  printf '['
  while IFS='|' read -r device target mode; do
    [ -n "${device}" ] || continue
    [ -n "${target}" ] || continue
    if [ "${first}" -eq 0 ]; then
      printf ','
    fi
    first=0
    printf '{'
    printf '"device":%s,' "$(json_string "${device}")"
    printf '"target":%s,' "$(json_string "${target}")"
    printf '"mode":%s' "$(json_string "${mode}")"
    printf '}'
  done < <(list_auto_mounts)
  printf ']'
}

command_json() {
  if "$@" 2>/dev/null; then
    return 0
  fi
  printf '{}'
}

mount_table_json() {
  local first=1
  local source
  local target
  local fstype
  local options
  local _rest

  printf '{"filesystems":['
  while read -r source target fstype options _rest; do
    [ -n "${target}" ] || continue
    if [ "${first}" -eq 0 ]; then
      printf ','
    fi
    first=0
    printf '{'
    printf '"target":%s,' "$(json_string "$(printf '%b' "${target}")")"
    printf '"source":%s,' "$(json_string "$(printf '%b' "${source}")")"
    printf '"fstype":%s,' "$(json_string "$(printf '%b' "${fstype}")")"
    printf '"options":%s' "$(json_string "$(printf '%b' "${options}")")"
    printf '}'
  done </proc/self/mounts
  printf ']}'
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

json_string() {
  if [ -n "${1+x}" ] && [ -n "$1" ]; then
    printf '"%s"' "$(escape_json "$1")"
  else
    printf 'null'
  fi
}

is_raid_member_type() {
  case "$1" in
    ddf_raid_member | linux_raid_member | isw_raid_member | lsi_mega_raid_member)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

is_supported_mount_type() {
  case "$1" in
    btrfs | ext4 | ext3 | ext2 | xfs | ntfs | ntfs3 | exfat | vfat)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

list_partition_nodes() {
  local root_device="$1"
  local candidate

  [ -n "${root_device}" ] || return 0

  for candidate in "${root_device}"[0-9]* "${root_device}"p[0-9]*; do
    [ -b "${candidate}" ] || continue
    printf '%s\n' "${candidate}"
  done
}

partition_table_rows() {
  local root_device="$1"

  command_exists fdisk || return 0
  [ -b "${root_device}" ] || return 0

  fdisk -l "${root_device}" 2>/dev/null | awk -v root="${root_device}" '
    $1 ~ ("^" root "([0-9]+|p[0-9]+)$") {
      start_col = 2
      boot = ""
      if ($2 == "*") {
        boot = "*"
        start_col = 3
      }

      type = ""
      for (i = start_col + 5; i <= NF; i++) {
        type = type (i == start_col + 5 ? "" : " ") $i
      }

      printf "%s|%s|%s|%s|%s|%s|%s|%s\n", $1, boot, $(start_col), $(start_col + 1), $(start_col + 2), $(start_col + 3), $(start_col + 4), type
    }
  '
}

list_probe_paths() {
  local root_device="$1"

  if [ -n "${root_device}" ]; then
    {
      lsblk -pnr -o PATH,TYPE,FSTYPE "${root_device}" 2>/dev/null | while read -r path type fstype; do
        case "${type}" in
          disk | part)
            if [ -n "${path}" ]; then
              printf '%s\n' "${path}"
            fi
            ;;
        esac
      done
      list_partition_nodes "${root_device}"
    } | awk '!seen[$0]++'
    return 0
  fi

  lsblk -pnr -o PATH,TYPE,FSTYPE 2>/dev/null | while read -r path type fstype; do
    case "${type}" in
      disk | part)
        if is_raid_member_type "${fstype}"; then
          printf '%s\n' "${path}"
        fi
        ;;
    esac
  done
}

device_has_mounted_descendants() {
  local root="$1"
  local mountpoint

  [ -n "${root}" ] || return 1

  while read -r mountpoint; do
    if [ -n "${mountpoint}" ] && [ "${mountpoint}" != "[SWAP]" ]; then
      return 0
    fi
  done < <(lsblk -pnr -o MOUNTPOINT "${root}" 2>/dev/null | tail -n +2)

  return 1
}

device_has_children() {
  local root="$1"
  local child

  [ -n "${root}" ] || return 1

  while read -r child; do
    if [ -n "${child}" ] && [ "${child}" != "${root}" ]; then
      return 0
    fi
  done < <(lsblk -pnr -o PATH "${root}" 2>/dev/null | tail -n +2)

  return 1
}

list_inactive_foreign_roots() {
  lsblk -pnr -o PATH,TYPE,FSTYPE 2>/dev/null | while read -r path type fstype; do
    [ "${type}" = "disk" ] || continue
    is_raid_member_type "${fstype}" || continue
    device_has_mounted_descendants "${path}" && continue
    printf '%s\n' "${path}"
  done
}

md_member_array_name() {
  local device="$1"
  local array_name=""

  array_name=$(mdadm_examine_field "${device}" "Name")
  if [ -z "${array_name}" ]; then
    array_name=$(detect_label "${device}")
  fi
  if [ -z "${array_name}" ]; then
    array_name=$(basename "${device}")
  fi

  sanitize_mount_name "${array_name}"
}

md_member_array_uuid() {
  local device="$1"
  local array_uuid=""

  array_uuid=$(mdadm_examine_field "${device}" "Array UUID")
  [ -n "${array_uuid}" ] || return 1
  printf '%s' "${array_uuid}"
}

md_member_import_name() {
  local device="$1"
  local sanitized_name=""
  local array_uuid=""
  local uuid_suffix=""

  sanitized_name=$(md_member_array_name "${device}")
  array_uuid=$(md_member_array_uuid "${device}" || true)
  uuid_suffix=$(printf '%s' "${array_uuid}" | tr -d ':' | cut -c1-8)

  sanitized_name=$(printf '%.12s' "${sanitized_name}")
  if [ -n "${uuid_suffix}" ]; then
    printf 'fnv-%s-%s' "${sanitized_name}" "${uuid_suffix}"
  else
    printf 'fnv-%s' "${sanitized_name}"
  fi
}

md_member_array_candidates() {
  local device="$1"
  local scanned_array=""
  local import_name=""
  local scanned_base=""

  command_exists mdadm || return 0
  [ -b "${device}" ] || return 0

  import_name=$(md_member_import_name "${device}")
  if [ -n "${import_name}" ]; then
    printf '/dev/md/%s\n' "${import_name}"
  fi

  scanned_array=$(mdadm --examine --scan "${device}" 2>/dev/null | awk '/^ARRAY / { print $2; exit }')
  scanned_base=$(basename "${scanned_array}")
  if [ -n "${scanned_array}" ] && ! printf '%s' "${scanned_base}" | grep -Eq '^[0-9]+$'; then
    printf '%s\n' "${scanned_array}"
  fi
}

md_array_matches_member() {
  local array_path="$1"
  local device="$2"
  local array_uuid=""
  local device_uuid=""

  [ -b "${array_path}" ] || return 1
  [ -b "${device}" ] || return 1
  command_exists mdadm || return 1

  device_uuid=$(md_member_array_uuid "${device}" || true)
  [ -n "${device_uuid}" ] || return 1

  array_uuid=$(mdadm --detail "${array_path}" 2>/dev/null | awk -F' : ' '
    $1 ~ /^[[:space:]]*UUID$/ {
      value = $2
      sub(/^[[:space:]]+/, "", value)
      sub(/[[:space:]]+$/, "", value)
      print value
      exit
    }
  ')
  [ -n "${array_uuid}" ] || return 1
  [ "${array_uuid}" = "${device_uuid}" ]
}

assemble_degraded_md_member() {
  local device="$1"
  local array_path=""

  command_exists mdadm || return 1
  [ -b "${device}" ] || return 1

  while read -r array_path; do
    [ -n "${array_path}" ] || continue

    if md_array_matches_member "${array_path}" "${device}"; then
      printf '%s' "${array_path}"
      return 0
    fi

    mdadm --assemble "${array_path}" --run --readonly --force "${device}" >>"${LOG_FILE}" 2>&1 || true
    if md_array_matches_member "${array_path}" "${device}"; then
      printf '%s' "${array_path}"
      return 0
    fi

    mdadm --assemble "${array_path}" --run --force "${device}" >>"${LOG_FILE}" 2>&1 || true
    if md_array_matches_member "${array_path}" "${device}"; then
      printf '%s' "${array_path}"
      return 0
    fi
  done < <(md_member_array_candidates "${device}" | awk '!seen[$0]++')

  return 1
}

share_link_name_for_target() {
  local target="$1"
  local name

  name=$(basename "${target}")
  printf '%s%s' "${APP_SHARE_PREFIX}" "${name}"
}

ensure_app_share_dir() {
  mkdir -p "${APP_SHARE_DIR}" >/dev/null 2>&1 || return 1
}

ensure_mount_root() {
  mkdir -p "${MOUNT_ROOT}" >/dev/null 2>&1 || return 1
}

mount_target_active() {
  local target="$1"
  local normalized_target

  [ -n "${target}" ] || return 1
  normalized_target=$(printf '%s' "${target}" | sed 's:/*$::')
  [ -n "${normalized_target}" ] || normalized_target="/"

  if command_exists mountpoint; then
    mountpoint -q "${normalized_target}" >/dev/null 2>&1
    return $?
  fi

  awk -v target="${normalized_target}" '$2 == target { found = 1; exit } END { exit(found ? 0 : 1) }' /proc/self/mounts >/dev/null 2>&1
}

mount_target_reusable() {
  local target="$1"

  [ -n "${target}" ] || return 1
  mount_target_active "${target}" && return 1
  [ -d "${target}" ] || return 1
  [ -z "$(find "${target}" -mindepth 1 -maxdepth 1 2>/dev/null | head -n 1)" ] || return 1
  return 0
}

list_managed_mount_targets() {
  local target=""

  if command_exists findmnt; then
    while read -r target; do
      case "${target}" in
        "${MOUNT_ROOT}" | "${MOUNT_ROOT}"/*)
          printf '%s\n' "${target}"
          ;;
      esac
    done < <(findmnt -rn -o TARGET 2>/dev/null)
  else
    while read -r _source target _fstype _options _rest; do
      target=$(printf '%b' "${target}")
      case "${target}" in
        "${MOUNT_ROOT}" | "${MOUNT_ROOT}"/*)
          printf '%s\n' "${target}"
          ;;
      esac
    done </proc/self/mounts
  fi
}

prune_stale_mount_dirs() {
  local path

  [ -d "${MOUNT_ROOT}" ] || return 0

  while read -r path; do
    [ -n "${path}" ] || continue
    mount_target_active "${path}" && continue
    [ -d "${path}" ] || continue
    [ -z "$(find "${path}" -mindepth 1 -maxdepth 1 2>/dev/null | head -n 1)" ] || continue
    rmdir "${path}" >/dev/null 2>&1 || true
    log_msg "pruned stale mount dir ${path}"
  done < <(find "${MOUNT_ROOT}" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort)
}

is_managed_mount_target() {
  case "$1" in
    "${APP_SHARE_ROOT}" | "${APP_SHARE_ROOT}"/* | "${MOUNT_ROOT}" | "${MOUNT_ROOT}"/*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

register_app_share() {
  local target="$1"
  local link_name
  local link_path

  [ -n "${target}" ] || return 1
  [ -d "${target}" ] || return 1
  if is_managed_mount_target "${target}"; then
    ensure_mount_root
    return $?
  fi
  ensure_app_share_dir || return 1

  link_name=$(share_link_name_for_target "${target}")
  link_path="${APP_SHARE_DIR}/${link_name}"

  ln -sfn "${target}" "${link_path}" || return 1
  log_msg "app share linked ${link_path} -> ${target}"
}

unregister_app_share() {
  local target="$1"
  local link_name
  local link_path

  [ -n "${target}" ] || return 0

  if is_managed_mount_target "${target}"; then
    ensure_mount_root
    return 0
  fi

  link_name=$(share_link_name_for_target "${target}")
  link_path="${APP_SHARE_DIR}/${link_name}"

  if [ -L "${link_path}" ] || [ -e "${link_path}" ]; then
    rm -f "${link_path}" || return 1
    log_msg "app share removed ${link_path}"
  fi
}

prune_stale_app_shares() {
  local link_path
  local target

  [ -d "${APP_SHARE_DIR}" ] || return 0

  while read -r link_path; do
    [ -n "${link_path}" ] || continue
    target=$(readlink "${link_path}" 2>/dev/null || true)
    case "${target}" in
      /vol[0-9]*)
        if ! findmnt -rn "${target}" >/dev/null 2>&1; then
          rm -f "${link_path}" || true
          log_msg "app share pruned ${link_path}"
        fi
        ;;
    esac
  done < <(find "${APP_SHARE_DIR}" -maxdepth 1 -type l -name "${APP_SHARE_PREFIX}*" 2>/dev/null)

  prune_stale_mount_dirs
}

mount_name_candidates() {
  local device="$1"
  local fstype="$2"
  local label
  local uuid
  local base

  label=$(detect_label "${device}")
  uuid=$(detect_uuid "${device}")
  base=$(basename "${device}")

  if [ -n "${label}" ]; then
    sanitize_mount_name "${label}"
    printf '\n'
  fi

  if [ -n "${base}" ]; then
    sanitize_mount_name "${base}"
    printf '\n'
  fi

  if [ -n "${uuid}" ]; then
    sanitize_mount_name "${uuid}"
    printf '\n'
  fi

  if [ -n "${fstype}" ]; then
    sanitize_mount_name "${fstype}"
    printf '\n'
  fi

  printf 'imported\n'
}

next_mount_point() {
  local device="$1"
  local fstype="$2"
  local name
  local candidate
  local suffix

  ensure_mount_root || return 1

  while read -r name; do
    [ -n "${name}" ] || continue
    candidate="${MOUNT_ROOT}/${name}"
    if mount_target_reusable "${candidate}"; then
      printf '%s' "${candidate}"
      return 0
    fi
    if ! mount_target_active "${candidate}" && [ ! -e "${candidate}" ]; then
      printf '%s' "${candidate}"
      return 0
    fi

    suffix=2
    while :; do
      candidate="${MOUNT_ROOT}/${name}-${suffix}"
      if mount_target_reusable "${candidate}"; then
        printf '%s' "${candidate}"
        return 0
      fi
      if ! mount_target_active "${candidate}" && [ ! -e "${candidate}" ]; then
        printf '%s' "${candidate}"
        return 0
      fi
      suffix=$((suffix + 1))
    done
  done < <(mount_name_candidates "${device}" "${fstype}" | awk '!seen[$0]++')

  return 1
}

detect_fs_type() {
  local device="$1"
  blkid -o value -s TYPE "${device}" 2>/dev/null || lsblk -no FSTYPE "${device}" 2>/dev/null | head -n 1
}

detect_uuid() {
  local device="$1"
  blkid -o value -s UUID "${device}" 2>/dev/null
}

detect_label() {
  local device="$1"
  blkid -o value -s LABEL "${device}" 2>/dev/null
}

detect_mountpoint() {
  local device="$1"
  lsblk -no MOUNTPOINT "${device}" 2>/dev/null | head -n 1
}

detect_mount_mode() {
  local target="$1"
  local device="${2:-}"
  local mount_options=""

  if [ -n "${target}" ] && command_exists findmnt; then
    mount_options=$(findmnt -rn "${target}" -o OPTIONS 2>/dev/null | head -n 1)
  fi

  if [ -z "${mount_options}" ] && [ -n "${device}" ] && command_exists findmnt; then
    mount_options=$(findmnt -rn -S "${device}" -o OPTIONS 2>/dev/null | head -n 1)
  fi

  case ",${mount_options}," in
    *,rw,*)
      printf 'rw'
      ;;
    *)
      printf 'ro'
      ;;
  esac
}

mdadm_examine_field() {
  local device="$1"
  local field_name="$2"

  command_exists mdadm || return 1
  [ -b "${device}" ] || return 1
  [ -n "${field_name}" ] || return 1

  mdadm --examine "${device}" 2>/dev/null | awk -F' : ' -v field="${field_name}" '
    $1 ~ ("^[[:space:]]*" field "$") {
      value = $2
      sub(/^[[:space:]]+/, "", value)
      sub(/[[:space:]]+$/, "", value)
      print value
      exit
    }
  '
}

md_member_data_offset_bytes() {
  local device="$1"
  local offset_field
  local offset_sectors

  offset_field=$(mdadm_examine_field "${device}" "Data Offset")
  [ -n "${offset_field}" ] || return 1

  offset_sectors=$(printf '%s' "${offset_field}" | awk '{ print $1 }')
  [ -n "${offset_sectors}" ] || return 1
  printf '%s' "$((offset_sectors * 512))"
}

is_degraded_md_mount_candidate() {
  local device="$1"
  local metadata_version
  local raid_level
  local data_offset

  [ -b "${device}" ] || return 1
  is_raid_member_type "$(detect_fs_type "${device}")" || return 1

  metadata_version=$(mdadm_examine_field "${device}" "Version")
  raid_level=$(mdadm_examine_field "${device}" "Raid Level")
  data_offset=$(md_member_data_offset_bytes "${device}" || true)

  [ "${metadata_version}" = "1.2" ] || return 1
  [ "${raid_level}" = "raid1" ] || return 1
  [ -n "${data_offset}" ] || return 1
  return 0
}

block_device_parent_path() {
  local device="$1"
  local parent_name=""

  [ -n "${device}" ] || return 1
  [ -b "${device}" ] || return 1

  parent_name=$(lsblk -dn -o PKNAME "${device}" 2>/dev/null | head -n 1)
  [ -n "${parent_name}" ] || return 1

  case "${parent_name}" in
    /dev/*)
      printf '%s' "${parent_name}"
      ;;
    *)
      printf '/dev/%s' "${parent_name}"
      ;;
  esac
}

device_requires_read_only_mount() {
  local device="$1"
  local visited_devices="${2:- }"
  local current_device=""
  local block_name=""
  local slave_path=""
  local slave_device=""
  local parent_device=""

  [ -n "${device}" ] || return 1
  [ -b "${device}" ] || return 1

  current_device="${device}"
  case "${visited_devices}" in
    *" ${current_device} "*)
      return 1
      ;;
  esac
  visited_devices="${visited_devices}${current_device} "

  if is_degraded_md_mount_candidate "${current_device}"; then
    return 0
  fi

  block_name=$(basename "$(readlink -f "${current_device}" 2>/dev/null || printf '%s' "${current_device}")")
  [ -n "${block_name}" ] || block_name=$(basename "${current_device}")

  for slave_path in /sys/class/block/"${block_name}"/slaves/*; do
    [ -e "${slave_path}" ] || continue
    slave_device="/dev/$(basename "${slave_path}")"
    if [ -b "${slave_device}" ] && device_requires_read_only_mount "${slave_device}" "${visited_devices}"; then
      return 0
    fi
  done

  parent_device=$(block_device_parent_path "${current_device}" || true)
  if [ -n "${parent_device}" ] && [ "${parent_device}" != "${current_device}" ]; then
    if device_requires_read_only_mount "${parent_device}" "${visited_devices}"; then
      return 0
    fi
  fi

  return 1
}

device_mountmode() {
  local device="$1"

  if device_requires_read_only_mount "${device}"; then
    printf 'ro'
  else
    printf 'rw'
  fi
}

partition_json() {
  local root="$1"
  local path="$2"
  local bootable="$3"
  local start="$4"
  local end="$5"
  local sectors="$6"
  local size="$7"
  local part_id="$8"
  local part_type="$9"
  local node_exists="false"
  local readable="false"
  local fstype=""
  local uuid=""
  local label=""
  local mountpoint=""
  local mountmode="rw"

  if [ -b "${path}" ]; then
    node_exists="true"
    if dd if="${path}" of=/dev/null bs=512 count=1 status=none 2>/dev/null; then
      readable="true"
    fi
    fstype=$(detect_fs_type "${path}")
    uuid=$(detect_uuid "${path}")
    label=$(detect_label "${path}")
    mountpoint=$(detect_mountpoint "${path}")
    mountmode=$(device_mountmode "${path}")
  fi

  printf '{'
  printf '"disk":%s,' "$(json_string "${root}")"
  printf '"path":%s,' "$(json_string "${path}")"
  printf '"bootable":%s,' "$([ "${bootable}" = "*" ] && printf true || printf false)"
  printf '"start":%s,' "$(json_string "${start}")"
  printf '"end":%s,' "$(json_string "${end}")"
  printf '"sectors":%s,' "$(json_string "${sectors}")"
  printf '"size":%s,' "$(json_string "${size}")"
  printf '"partId":%s,' "$(json_string "${part_id}")"
  printf '"partType":%s,' "$(json_string "${part_type}")"
  printf '"nodeExists":%s,' "${node_exists}"
  printf '"readable":%s,' "${readable}"
  printf '"fstype":%s,' "$(json_string "${fstype}")"
  printf '"label":%s,' "$(json_string "${label}")"
  printf '"uuid":%s,' "$(json_string "${uuid}")"
  printf '"mountpoint":%s,' "$(json_string "${mountpoint}")"
  printf '"mountmode":%s' "$(json_string "${mountmode}")"
  printf '}'
}

disk_inventory_json() {
  local first_disk=1
  local first_part
  local root type size fstype label uuid mountpoint
  local path bootable start end sectors part_size part_id part_type

  printf '{"disks":['

  while read -r root type size fstype label uuid mountpoint; do
    [ "${type}" = "disk" ] || continue

    if [ "${first_disk}" -eq 0 ]; then
      printf ','
    fi
    first_disk=0

    printf '{'
    printf '"path":%s,' "$(json_string "${root}")"
    printf '"size":%s,' "$(json_string "${size}")"
    printf '"fstype":%s,' "$(json_string "${fstype}")"
    printf '"label":%s,' "$(json_string "${label}")"
    printf '"uuid":%s,' "$(json_string "${uuid}")"
    printf '"mountpoint":%s,' "$(json_string "${mountpoint}")"
    printf '"partitions":['

    first_part=1
    while IFS='|' read -r path bootable start end sectors part_size part_id part_type; do
      [ -n "${path}" ] || continue
      if [ "${first_part}" -eq 0 ]; then
        printf ','
      fi
      first_part=0
      partition_json "${root}" "${path}" "${bootable}" "${start}" "${end}" "${sectors}" "${part_size}" "${part_id}" "${part_type}"
    done < <(partition_table_rows "${root}")

    printf ']'
    printf '}'
  done < <(lsblk -dnpr -o PATH,TYPE,SIZE,FSTYPE,LABEL,UUID,MOUNTPOINT 2>/dev/null)

  printf ']}'
}

mount_options() {
  local fstype="$1"
  local mode="$2"
  case "${fstype}" in
    btrfs)
      if [ "${mode}" = "ro" ]; then
        printf 'ro,relatime,rescue=nologreplay,space_cache=v2'
      else
        printf 'rw,relatime,space_cache=v2'
      fi
      ;;
    ext2 | ext3 | ext4)
      if [ "${mode}" = "ro" ]; then
        printf 'ro,noload'
      else
        printf 'rw'
      fi
      ;;
    xfs)
      if [ "${mode}" = "ro" ]; then
        printf 'ro,norecovery'
      else
        printf 'rw'
      fi
      ;;
    ntfs)
      if [ "${mode}" = "ro" ]; then
        printf 'ro'
      else
        printf 'rw'
      fi
      ;;
    ntfs3 | exfat | vfat)
      if [ "${mode}" = "ro" ]; then
        printf 'ro'
      else
        printf 'rw'
      fi
      ;;
    *)
      if [ "${mode}" = "ro" ]; then
        printf 'ro'
      else
        printf 'rw'
      fi
      ;;
  esac
}

normalize_mount_fstype() {
  case "$1" in
    ntfs)
      printf 'ntfs3'
      ;;
    *)
      printf '%s' "$1"
      ;;
  esac
}

emit_json_field() {
  local field_name="$1"
  shift

  printf '"%s":' "${field_name}"
  "$@"
}

emit_status_json() {
  printf '{'
  printf '"timestamp":"%s",' "$(date '+%Y-%m-%d %H:%M:%S')"
  printf '"mountRoot":"%s",' "${MOUNT_ROOT}"
  printf '"mountAliasRoot":"%s",' "${APP_SHARE_ROOT}"
  emit_json_field "lsblk" command_json lsblk -J -p -o PATH,NAME,TYPE,SIZE,FSTYPE,LABEL,UUID,MOUNTPOINT,PKNAME
  printf ','
  emit_json_field "inventory" disk_inventory_json
  printf ','
  emit_json_field "findmnt" mount_table_json
  printf ','
  emit_json_field "autoMounts" auto_mounts_json
  printf ','
  emit_json_field "vgs" command_json vgs --reportformat json --units b --nosuffix -o vg_name,vg_uuid,pv_count,lv_count
  printf ','
  emit_json_field "lvs" command_json lvs --reportformat json --units b --nosuffix -o lv_path,lv_name,vg_name,lv_size,lv_attr
  printf ','
  emit_json_field "pvs" command_json pvs --reportformat json --units b --nosuffix -o pv_name,vg_name,pv_uuid,pv_size,pv_attr
  printf ','
  printf '"mdstat":"%s",' "$(cat /proc/mdstat 2>/dev/null | escape_json)"
  printf '"logTail":"%s"' "$(tail -n 120 "${LOG_FILE}" 2>/dev/null | escape_json)"
  printf '}'
}

url_decode() {
  local value="${1//+/ }"
  printf '%b' "${value//%/\\x}"
}

initialize_request_context() {
  request_action=""
  request_device=""
  request_mode="ro"
  request_target=""
  request_auto="1"
  effective_mode=""
  state_device=""
  mount_device=""
}

read_request_body() {
  if [ -n "${CONTENT_LENGTH:-}" ] && [ "${CONTENT_LENGTH}" -gt 0 ] 2>/dev/null; then
    dd bs=1 count="${CONTENT_LENGTH}" 2>/dev/null
  fi
}

build_request_data() {
  local request_query="${QUERY_STRING:-}"
  local request_body=""

  request_body=$(read_request_body)

  if [ -n "${request_query}" ] && [ -n "${request_body}" ]; then
    printf '%s&%s' "${request_query}" "${request_body}"
    return 0
  fi

  if [ -n "${request_query}" ]; then
    printf '%s' "${request_query}"
    return 0
  fi

  printf '%s' "${request_body}"
}

parse_request_data() {
  local request_data="$1"
  local original_ifs
  local pair
  local field_name
  local field_value

  original_ifs=$IFS
  set -f
  IFS='&'
  set -- ${request_data}
  IFS=$original_ifs
  set +f

  for pair in "$@"; do
    field_name=${pair%%=*}
    field_value=${pair#*=}
    case "${field_name}" in
      action)
        request_action=$(url_decode "${field_value}")
        ;;
      device)
        request_device=$(url_decode "${field_value}")
        ;;
      mode)
        request_mode=$(url_decode "${field_value}")
        ;;
      target)
        request_target=$(url_decode "${field_value}")
        ;;
      auto)
        request_auto=$(url_decode "${field_value}")
        ;;
    esac
  done
}

default_request_action() {
  if [ -z "${request_action}" ] && [ "${REQUEST_METHOD:-GET}" = "GET" ]; then
    request_action="status"
  fi
}

send_json_header() {
  echo "Content-Type: application/json; charset=utf-8"
  echo ""
}

send_response() {
  local ok="$1"
  local message="$2"
  printf '{"ok":%s,"message":"%s","status":%s}\n' "${ok}" "$(escape_json "${message}")" "$(emit_status_json)"
  exit 0
}

send_error() {
  log_msg "ERROR: $*"
  send_response false "$*"
}

resolve_request_mount_device() {
  local requested_device="$1"
  local resolved_device=""

  state_device="${requested_device}"
  mount_device="${requested_device}"

  case "${requested_device}" in
    /dev/mapper/* | /dev/md*)
      return 0
      ;;
  esac

  if is_degraded_md_mount_candidate "${requested_device}"; then
    resolved_device=$(assemble_degraded_md_member "${requested_device}" || true)
    if [ -n "${resolved_device}" ]; then
      mount_device="${resolved_device}"
    fi
  fi
}

enforce_mount_mode() {
  local requested_mode="$1"
  local requested_device="$2"
  local resolved_device="$3"

  if [ "${requested_mode}" != "rw" ]; then
    printf 'ro'
    return 0
  fi

  if [ "$(device_mountmode "${resolved_device}")" = "ro" ] || [ "$(device_mountmode "${requested_device}")" = "ro" ]; then
    log_msg "force read-only mount for ${requested_device} via ${resolved_device}"
    printf 'ro'
    return 0
  fi

  printf 'rw'
}

activate_degraded_md_members() {
  local block_device="$1"
  local candidate
  local assembled_device

  while read -r candidate; do
    [ -b "${candidate}" ] || continue
    is_degraded_md_mount_candidate "${candidate}" || continue

    assembled_device=$(assemble_degraded_md_member "${candidate}" || true)
    if [ -n "${assembled_device}" ]; then
      log_msg "md member assembled ${candidate} -> ${assembled_device}"
      if command_exists pvscan; then
        pvscan --cache "${assembled_device}" >>"${LOG_FILE}" 2>&1 || true
      fi
    fi
  done < <(list_probe_paths "${block_device}")
}

cleanup_import_device_stack() {
  local source_device="$1"
  local vg_name
  local lineage_paths=()
  local current_path=""
  local idx

  [ -n "${source_device}" ] || return 0
  [ -b "${source_device}" ] || return 0

  current_path="${source_device}"
  while [ -n "${current_path}" ] && [ -b "${current_path}" ]; do
    lineage_paths+=("${current_path}")
    current_path=$(block_device_parent_path "${current_path}" || true)
    case " ${lineage_paths[*]} " in
      *" ${current_path} "*)
        break
        ;;
    esac
  done

  [ "${#lineage_paths[@]}" -gt 0 ] || return 0

  while read -r vg_name; do
    [ -n "${vg_name}" ] || continue
    if vg_has_mounted_lvs "${vg_name}"; then
      log_msg "cleanup kept vg ${vg_name}: logical volumes still mounted"
      continue
    fi
    if command_exists vgchange; then
      log_msg "deactivate volume group ${vg_name}"
      vgchange -an "${vg_name}" >>"${LOG_FILE}" 2>&1 || true
    fi
  done < <(find_vgs_for_paths "${lineage_paths[@]}" | awk '!seen[$0]++')

  for ((idx = 0; idx < ${#lineage_paths[@]}; idx++)); do
    current_path="${lineage_paths[$idx]}"
    case "${current_path}" in
      /dev/mapper/*)
        if device_has_mounted_descendants "${current_path}"; then
          continue
        fi
        if device_has_children "${current_path}"; then
          continue
        fi
        if command_exists dmsetup; then
          log_msg "remove mapper device ${current_path}"
          dmsetup remove "$(basename "${current_path}")" >>"${LOG_FILE}" 2>&1 || true
        fi
        ;;
      /dev/md*)
        if device_has_mounted_descendants "${current_path}"; then
          continue
        fi
        if device_has_children "${current_path}"; then
          continue
        fi
        if command_exists mdadm; then
          log_msg "stop md device ${current_path}"
          mdadm --stop "${current_path}" >>"${LOG_FILE}" 2>&1 || true
        fi
        ;;
    esac
  done
}

scan_storage_stack() {
  if command_exists pvscan; then
    pvscan --cache >>"${LOG_FILE}" 2>&1 || pvscan >>"${LOG_FILE}" 2>&1 || true
  fi

  if command_exists vgscan; then
    vgscan --mknodes >>"${LOG_FILE}" 2>&1 || true
  fi

  if command_exists vgchange; then
    vgchange -ay >>"${LOG_FILE}" 2>&1 || true
  fi

  if command_exists btrfs; then
    btrfs device scan >>"${LOG_FILE}" 2>&1 || true
  fi
}

refresh_block_device_topology() {
  local block_device="$1"

  [ -n "${block_device}" ] || return 0
  [ -b "${block_device}" ] || return 0

  if command_exists blockdev; then
    blockdev --rereadpt "${block_device}" >>"${LOG_FILE}" 2>&1 || true
  fi

  if command_exists partprobe; then
    partprobe "${block_device}" >>"${LOG_FILE}" 2>&1 || true
  fi

  if command_exists partx; then
    partx -u "${block_device}" >>"${LOG_FILE}" 2>&1 || true
    partx -a "${block_device}" >>"${LOG_FILE}" 2>&1 || true
  fi

  if command_exists udevadm; then
    udevadm settle >>"${LOG_FILE}" 2>&1 || true
  fi
}

vg_has_mounted_lvs() {
  local vg_name="$1"
  local lv_path

  [ -n "${vg_name}" ] || return 1
  command_exists lvs || return 1

  while read -r lv_path; do
    lv_path=$(printf '%s' "${lv_path}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [ -n "${lv_path}" ] || continue
    if findmnt -rn -S "${lv_path}" >/dev/null 2>&1; then
      return 0
    fi
  done < <(lvs --noheadings -o lv_path "${vg_name}" 2>/dev/null)

  return 1
}

find_vgs_for_paths() {
  local tmp_file
  local path
  local pv_name
  local vg_name

  command_exists pvs || return 0
  [ "$#" -gt 0 ] || return 0

  tmp_file=$(mktemp "${APP_VAR_DIR}/paths.XXXXXX") || return 0
  for path in "$@"; do
    [ -n "${path}" ] || continue
    printf '%s\n' "${path}" >>"${tmp_file}"
  done

  while read -r pv_name vg_name; do
    pv_name=$(printf '%s' "${pv_name}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    vg_name=$(printf '%s' "${vg_name}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [ -n "${pv_name}" ] || continue
    [ -n "${vg_name}" ] || continue
    if grep -Fxq "${pv_name}" "${tmp_file}"; then
      printf '%s\n' "${vg_name}"
    fi
  done < <(pvs --noheadings -o pv_name,vg_name 2>/dev/null)

  rm -f "${tmp_file}"
}

unmount_managed_target() {
  local managed_target="$1"
  local preserve_auto_state="${2:-0}"
  local source_device=""

  [ -n "${managed_target}" ] || return 0

  is_managed_mount_target "${managed_target}" || return 1
  findmnt -rn "${managed_target}" >/dev/null 2>&1 || return 0

  source_device=$(findmnt -rn "${managed_target}" -o SOURCE 2>/dev/null | head -n 1)

  log_msg "unmount ${managed_target}"
  if ! umount "${managed_target}" >>"${LOG_FILE}" 2>&1; then
    log_msg "regular unmount failed for ${managed_target}, trying lazy unmount"
    sync >>"${LOG_FILE}" 2>&1 || true
    umount -l "${managed_target}" >>"${LOG_FILE}" 2>&1 || return 1
  fi

  unregister_app_share "${managed_target}" >>"${LOG_FILE}" 2>&1 || log_msg "app share cleanup skipped for ${managed_target}"
  if [ "${preserve_auto_state}" != "1" ]; then
    forget_auto_mount "" "${managed_target}" >>"${LOG_FILE}" 2>&1 || log_msg "auto-mount state cleanup skipped for ${managed_target}"
  fi
  if [ "${managed_target}" != "${MOUNT_ROOT}" ]; then
    rmdir "${managed_target}" >/dev/null 2>&1 || true
  fi

  if [ -n "${source_device}" ]; then
    cleanup_import_device_stack "${source_device}"
  fi

  return 0
}

shutdown_managed_mounts() {
  local managed_target=""
  local failed=0

  while read -r managed_target; do
    [ -n "${managed_target}" ] || continue
    if ! unmount_managed_target "${managed_target}" 1; then
      failed=1
      log_msg "shutdown unmount failed for ${managed_target}"
    fi
  done < <(list_managed_mount_targets | awk '{ print length($0) "|" $0 }' | sort -rn | cut -d'|' -f2-)

  prune_stale_app_shares

  [ "${failed}" -eq 0 ]
}

md_device_is_inactive() {
  local md_path="$1"
  local md_name=""

  [ -n "${md_path}" ] || return 1
  md_name=$(basename "${md_path}")
  [ -n "${md_name}" ] || return 1

  awk -v name="${md_name}" '
    $1 == name && $2 == ":" && $3 == "inactive" {
      found = 1
      exit
    }
    END { exit(found ? 0 : 1) }
  ' /proc/mdstat >/dev/null 2>&1
}

stop_inactive_parent_md_children() {
  local block_device="$1"
  local md_child

  command_exists mdadm || return 0
  [ -b "${block_device}" ] || return 0

  while read -r md_child; do
    [ -b "${md_child}" ] || continue
    md_device_is_inactive "${md_child}" || continue
    log_msg "stop inactive parent md ${md_child} for ${block_device}"
    mdadm --stop "${md_child}" >>"${LOG_FILE}" 2>&1 || true
  done < <(lsblk -pnr -o PATH,TYPE "${block_device}" 2>/dev/null | awk -v root="${block_device}" '
    $1 != root && ($2 == "md" || $2 ~ /^raid/) { print $1 }
  ' | awk '!seen[$0]++')
}

probe_partitions_missing() {
  local block_device="$1"
  local partition_count=0

  [ -b "${block_device}" ] || return 1

  while read -r _partition_path; do
    partition_count=$((partition_count + 1))
    break
  done < <(list_partition_nodes "${block_device}")

  [ "${partition_count}" -eq 0 ]
}

refresh_manual_probe_roots() {
  local block_device="$1"
  local candidate_root

  if [ -n "${block_device}" ] && [ -b "${block_device}" ]; then
    refresh_block_device_topology "${block_device}"
    stop_inactive_parent_md_children "${block_device}"
    if probe_partitions_missing "${block_device}"; then
      refresh_block_device_topology "${block_device}"
    fi
    return 0
  fi

  while read -r candidate_root; do
    [ -b "${candidate_root}" ] || continue
    refresh_block_device_topology "${candidate_root}"
    stop_inactive_parent_md_children "${candidate_root}"
    if probe_partitions_missing "${candidate_root}"; then
      refresh_block_device_topology "${candidate_root}"
    fi
  done < <(list_inactive_foreign_roots)
}

manually_assemble_all_arrays() {
  local block_device="$1"

  refresh_manual_probe_roots "${block_device}"
  activate_degraded_md_members "${block_device}"
}

activate_storage_stack() {
  local block_device="$1"

  manually_assemble_all_arrays "${block_device}"
  scan_storage_stack
}

probe_block_device() {
  local block_device="$1"

  [ -b "${block_device}" ] || send_error "Device not found: ${block_device}"

  log_msg "probe ${block_device}"

  refresh_block_device_topology "${block_device}"

  activate_storage_stack "${block_device}"
}

dispatch_request() {
  case "${request_action}" in
    "" | status)
      emit_status_json
      ;;
    activate)
      log_msg "activate requested"
      activate_storage_stack
      prune_stale_app_shares
      send_response true "Foreign arrays and volume groups activated"
      ;;
    probe)
      [ -n "${request_device}" ] || send_error "Missing device parameter"
      case "${request_device}" in
        /dev/*) ;;
        *)
          send_error "Only /dev block devices can be probed"
          ;;
      esac
      probe_block_device "${request_device}"
      send_response true "Device probed and arrays activated"
      ;;
    mount)
      [ -n "${request_device}" ] || send_error "Missing device parameter"
      case "${request_device}" in
        /dev/*) ;;
        *)
          send_error "Only /dev block devices can be mounted"
          ;;
      esac

      resolve_request_mount_device "${request_device}"
      [ -b "${mount_device}" ] || send_error "Device not found: ${request_device}"

      fstype=$(detect_fs_type "${mount_device}")
      [ -n "${fstype}" ] || send_error "Failed to detect filesystem type"

      is_supported_mount_type "${fstype}" || send_error "Unsupported filesystem: ${fstype}"

      request_mode=$(enforce_mount_mode "${request_mode}" "${state_device}" "${mount_device}")

      existing_target=$(detect_active_mountpoint "${mount_device}" || true)
      if [ -z "${existing_target}" ] && [ "${state_device}" != "${mount_device}" ]; then
        existing_target=$(detect_active_mountpoint "${state_device}" || true)
      fi

      if [ -z "${request_target}" ]; then
        if [ -n "${existing_target}" ] && is_managed_mount_target "${existing_target}"; then
          effective_mode=$(detect_mount_mode "${existing_target}" "${mount_device}")
          if [ "${request_auto}" = "0" ] || [ "${request_auto}" = "false" ]; then
            forget_auto_mount "${state_device}" "${existing_target}" >>"${LOG_FILE}" 2>&1 || log_msg "auto-mount state cleanup skipped for ${state_device}"
          else
            remember_auto_mount "${state_device}" "${existing_target}" "${effective_mode}" >>"${LOG_FILE}" 2>&1 || log_msg "auto-mount state update skipped for ${state_device}"
          fi
          send_response true "Mounted at $(mount_alias_path "${existing_target}")"
        fi
        request_target=$(next_mount_point "${state_device}" "${fstype}") || send_error "Failed to allocate import mount path"
      else
        is_managed_mount_target "${request_target}" || send_error "Mount target must be under ${APP_SHARE_ROOT}"
        request_target=$(resolve_mount_target "${request_target}") || send_error "Invalid mount target: ${request_target}"
      fi

      if [ -n "${existing_target}" ]; then
        if is_legacy_mount_target "${existing_target}"; then
          log_msg "migrate legacy mount ${existing_target} -> ${request_target}"
          if migrate_managed_mount "${existing_target}" "${request_target}"; then
            send_response true "Mounted at $(mount_alias_path "${request_target}")"
          fi

          log_msg "legacy move unsupported, remount ${existing_target} -> ${request_target}"
          if ! umount "${existing_target}" >>"${LOG_FILE}" 2>&1; then
            sync >>"${LOG_FILE}" 2>&1 || true
            umount -l "${existing_target}" >>"${LOG_FILE}" 2>&1 || send_error "Failed to release legacy mount: ${existing_target}"
          fi
          rmdir "${existing_target}" >/dev/null 2>&1 || true
          existing_target=""
        else
          send_error "Device already mounted at ${existing_target}"
        fi
      fi

      mkdir -p "${request_target}" || send_error "Failed to create mount directory ${request_target}"
      if findmnt -rn "${request_target}" >/dev/null 2>&1; then
        send_error "Mount point already in use: ${request_target}"
      fi

      log_msg "mount ${mount_device} (${state_device}) to ${request_target} as ${fstype} (${request_mode})"
      mount -t "$(normalize_mount_fstype "${fstype}")" -o "$(mount_options "${fstype}" "${request_mode}")" "${mount_device}" "${request_target}" >>"${LOG_FILE}" 2>&1 || send_error "Mount failed: ${request_device}"
      effective_mode=$(detect_mount_mode "${request_target}" "${mount_device}")
      register_app_share "${request_target}" >>"${LOG_FILE}" 2>&1 || log_msg "app share registration skipped for ${request_target}"
      if [ "${request_auto}" = "0" ] || [ "${request_auto}" = "false" ]; then
        forget_auto_mount "${state_device}" "${request_target}" >>"${LOG_FILE}" 2>&1 || log_msg "auto-mount state cleanup skipped for ${state_device}"
      else
        remember_auto_mount "${state_device}" "${request_target}" "${effective_mode}" >>"${LOG_FILE}" 2>&1 || log_msg "auto-mount state update skipped for ${state_device}"
      fi
      send_response true "Mounted at $(mount_alias_path "${request_target}")"
      ;;
    unmount)
      [ -n "${request_target}" ] || send_error "Missing mount target parameter"
      is_managed_mount_target "${request_target}" || send_error "Only imported mount path can be unmounted"
      request_target=$(resolve_mount_target "${request_target}") || send_error "Invalid mount target: ${request_target}"

      findmnt -rn "${request_target}" >/dev/null 2>&1 || send_error "Mount point is not active: ${request_target}"
      unmount_managed_target "${request_target}" 0 || send_error "Unmount failed: ${request_target}"
      send_response true "Unmounted $(mount_alias_path "${request_target}") and released idle import resources"
      ;;
    shutdown)
      log_msg "shutdown requested"
      shutdown_managed_mounts || send_error "Failed to fully unmount imported volumes"
      send_response true "Imported volumes unmounted and import resources released"
      ;;
    auto-mount)
      [ -n "${request_device}" ] || send_error "Missing device parameter"
      case "${request_device}" in
        /dev/*) ;;
        *)
          send_error "Only /dev block devices are supported"
          ;;
      esac

      resolve_request_mount_device "${request_device}"
      request_device="${state_device}"

      if [ -n "${request_target}" ]; then
        is_managed_mount_target "${request_target}" || send_error "Mount target must be under ${APP_SHARE_ROOT}"
        request_target=$(resolve_mount_target "${request_target}") || send_error "Invalid mount target: ${request_target}"
      else
        request_target=$(detect_active_mountpoint "${request_device}" || true)
        if [ -z "${request_target}" ] && [ "${mount_device}" != "${request_device}" ]; then
          request_target=$(detect_active_mountpoint "${mount_device}" || true)
        fi
      fi

      [ -n "${request_target}" ] || send_error "Device is not mounted: ${request_device}"
      is_managed_mount_target "${request_target}" || send_error "Only imported mount path can be configured"

      if [ "${request_auto}" = "0" ] || [ "${request_auto}" = "false" ]; then
        forget_auto_mount "${request_device}" "${request_target}" >>"${LOG_FILE}" 2>&1 || log_msg "auto-mount state cleanup skipped for ${request_device}"
        send_response true "Auto-mount disabled for $(mount_alias_path "${request_target}")"
      fi

      effective_mode=$(enforce_mount_mode "${request_mode}" "${request_device}" "${mount_device}")
      if [ "${effective_mode}" != "rw" ]; then
        effective_mode=$(detect_mount_mode "${request_target}" "${request_device}")
      fi
      remember_auto_mount "${request_device}" "${request_target}" "${effective_mode}" >>"${LOG_FILE}" 2>&1 || send_error "Failed to update auto-mount state"
      send_response true "Auto-mount enabled for $(mount_alias_path "${request_target}")"
      ;;
    cleanup)
      log_msg "cleanup requested"
      prune_stale_app_shares
      send_response true "Idle import resources released"
      ;;
    *)
      send_error "Unsupported action"
      ;;
  esac
}

main() {
  send_json_header
  initialize_request_context
  parse_request_data "$(build_request_data)"
  default_request_action
  dispatch_request
}

main "$@"
