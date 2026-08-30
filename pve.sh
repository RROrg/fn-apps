#!/usr/bin/env bash
#
# Copyright (C) 2022 Ing <https://github.com/wjz304>
#
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#

# 参数
ONBOOT=1      # 开机启动，默认1
TYPE="fnos"   # 类型，支持 fnos 和 fygonas，默认 fnos
ARCH="x86_64" # 架构，支持 x86_64 和 aarch64，默认 x86_64
EFI=1         # 启用 UEFI 引导，默认1
ISO=""        # 本地ISO路径，默认空
STORAGE=""    # 存储，默认自动获取
V9PPATH=""    # 添加 virtio9p 挂载目录，默认空不添加
VFSDIRID=""   # 添加 virtiofs 挂载文件夹id，默认空不添加

usage() {
  echo "Usage: $0 [--onboot <0|1>] [--arch <x86_64|aarch64>] [--efi <0|1>] [--iso <path>]"
  echo "          [--storage <name>] [--v9ppath <path>] [--vfsdirid <dirid>]"
  echo ""
  echo "  --onboot <0|1>             Enable VM on boot, default 1 (enable)"
  echo "  --type <fnos|fygonas>      Type, support fnos and fygonas, default fnos"
  echo "  --arch <x86_64|aarch64>    Architecture, support x86_64 and aarch64, default x86_64"
  echo "  --efi <0|1>                Enable UEFI boot, default 1 (enable)"
  echo "  --iso <path>               Local ISO path, use local ISO if set"
  echo "  --storage <name>           Storage name for images, as local-lvm, default auto get"
  echo "  --v9ppath <path>           Set to /path/to/9p to mount virtio 9p share"
  echo "  --vfsdirid <dirid>         Set to <dirid> to mount virtio fs share"
}

ARGS=$(getopt -o '' --long onboot:,type:,arch:,efi:,iso:,storage:,v9ppath:,vfsdirid: -n "$0" -- "$@")
if [ $? -ne 0 ]; then
  usage
  exit 1
fi
eval set -- "$ARGS"
while true; do
  case "$1" in
    --onboot)
      ONBOOT="$2"
      echo "$ONBOOT" | grep -qvE '^(0|1)$' && ONBOOT=1
      shift 2
      ;;
    --type)
      TYPE="$2"
      echo "$TYPE" | grep -qvE '^(fnos|fygonas)$' && TYPE="fnos"
      shift 2
      ;;
    --arch)
      ARCH="$2"
      echo "$ARCH" | grep -qvE '^(x86_64|aarch64)$' && ARCH="x86_64"
      shift 2
      ;;
    --efi)
      EFI="$2"
      echo "$EFI" | grep -qvE '^(0|1)$' && EFI=1
      shift 2
      ;;
    --iso)
      ISO="$2"
      [ -f "${ISO}" ] && ISO="$(realpath "${ISO}")" || ISO=""
      shift 2
      ;;
    --storage)
      STORAGE="$2"
      [ -n "${STORAGE}" ] && pvesm status -content images | grep -qw "^${STORAGE}" || STORAGE=""
      shift 2
      ;;
    --v9ppath)
      V9PPATH="$2"
      [ -d "${V9PPATH}" ] && V9PPATH="$(realpath "${V9PPATH}")" || V9PPATH=""
      shift 2
      ;;
    --vfsdirid)
      VFSDIRID="$2"
      [ -n "${VFSDIRID}" ] && pvesh ls /cluster/mapping/dir | grep -qw "${VFSDIRID}" || VFSDIRID=""
      shift 2
      ;;
    --)
      shift
      break
      ;;
    *)
      usage
      exit 1
      ;;
  esac
done

if ! command -v qm >/dev/null 2>&1; then
  echo "Not a Proxmox VE environment"
  exit 1
fi

if [ -n "${ISO}" ] && [ -f "${ISO}" ]; then
  ISO_PATH="${ISO}"
else
  if ! command -v curl >/dev/null 2>&1; then
    apt update >/dev/null 2>&1 && apt install -y curl >/dev/null 2>&1
  fi
  if ! command -v jq >/dev/null 2>&1; then
    apt update >/dev/null 2>&1 && apt install -y jq >/dev/null 2>&1
  fi
  if [ "${TYPE}" = "fnos" ]; then
    if [ "$ARCH" = "x86_64" ]; then
      ISO_URL="$(curl -sL "https://www.fnnas.com/download?key=fnos" | grep -oP '{(?:[^{}]*fnos[^,]*\.iso[^{}]*thunder|[^{}]*thunder[^{}]*fnos[^,]*\.iso)[^}]*"}' | sort -u | sed 's/\\\"/"/g' | jq -rs '.[0].thunder // empty' 2>/dev/null | sed 's/^thunder:\/\///' | base64 -d 2>/dev/null | sed 's/^AA//; s/ZZ$//')"
    else
      ISO_URL="$(curl -sL "https://www.fnnas.com/download-arm" | grep -oP '{(?:[^{}]*fnos[^,]*\.iso[^{}]*thunder|[^{}]*thunder[^{}]*fnos[^,]*\.iso)[^}]*"}' | sort -u | sed 's/\\\"/"/g' | jq -rs '.[0].thunder // empty' 2>/dev/null | sed 's/^thunder:\/\///' | base64 -d 2>/dev/null | sed 's/^AA//; s/ZZ$//')"
    fi
  else
    if [ "$ARCH" = "x86_64" ]; then
      ISO_URL="$(curl -sL "https://fygonas.com/download" | grep -oP '{[^{}]*fygoos[^,]*\.iso[^}]*"}' | grep x86 | sort -u | sed 's/\\\"/"/g' | jq -rs '.[0].url // empty' 2>/dev/null)"
    else
      ISO_URL="$(curl -sL "https://fygonas.com/download" | grep -oP '{[^{}]*fygoos[^,]*\.iso[^}]*"}' | grep arm | sort -u | sed 's/\\\"/"/g' | jq -rs '.[0].url // empty' 2>/dev/null)"
    fi
  fi
  [ -z "${ISO_URL}" ] && {
    echo "Failed to retrieve ${TYPE}-${ARCH} ISO URL"
    exit 1
  }
  echo "Downloading ${TYPE}-${ARCH} ISO ... "
  ISO_PATH="/var/lib/vz/template/iso/$(basename "${ISO_URL}")"
  rm -f "${ISO_PATH}" || true
  mkdir -p /var/lib/vz/template/iso >/dev/null 2>&1
  STATUS=$(curl -skL --connect-timeout 10 -w "%{http_code}" "${ISO_URL}" -o "${ISO_PATH}")
  if [ "${STATUS}" -ne 200 ]; then
    echo "Failed to download ${TYPE}-${ARCH} ISO." >&2
    exit 1
  fi
fi

echo "Creating VM with ${TYPE}-${ARCH} ... "

# 获取可用的 VMID
LAST_VMID=$(qm list | awk 'NR>1{print $1}' | sort -n | tail -1 2>/dev/null)
VMID=$((${LAST_VMID:-99} + 1))

ARGS=""
SATAIDX=0

# 创建 VM
# vga.type: 'cirrus, qxl, qxl2, qxl3, qxl4, none, serial0, serial1, serial2, serial3, std, virtio, virtio-gl, vmware'
if [ "$ARCH" = "x86_64" ]; then
  qm create ${VMID} --name ${TYPE}-amd64 --arch x86_64 --machine q35 --ostype l26 --vga virtio --sockets 1 --cores 2 --cpu host --numa 0 --memory 4096 --scsihw virtio-scsi-single
else
  qm create ${VMID} --name ${TYPE}-arm64 --arch aarch64 --machine virt --ostype l26 --vga std --sockets 1 --cores 2 --cpu cortex-a72 --numa 0 --memory 4096 --scsihw virtio-scsi-single
fi
if [ $? -ne 0 ]; then
  echo "Create VM failed"
  exit 1
fi

# 获取 存储
[ -z "${STORAGE}" ] && STORAGE=$(pvesm status -content images | awk 'NR>1 {print $1}' | grep local | tail -1)
if [ -z "${STORAGE}" ]; then
  echo "No storage for images"
  qm destroy ${VMID} --purge
  exit 1
fi

# 启用 UEFI 引导
if [ "${EFI:-1}" -eq 1 ] || [ ! "${ARCH}" = "x86_64" ]; then
  if ! qm set ${VMID} --bios ovmf --efidisk0 ${STORAGE}:4,efitype=4m,pre-enrolled-keys=0; then
    echo "Set UEFI failed"
    qm destroy ${VMID} --purge
    exit 1
  fi
fi

if [ -d "${V9PPATH}" ]; then
  [ "virtio9p" = "${VFSDIRID}" ] && V9PTAG="virtio9p0" || V9PTAG="virtio9p"
  ARGS+="-fsdev local,security_model=passthrough,id=fsdev0,path=${V9PPATH} -device virtio-9p-pci,id=fs0,fsdev=fsdev0,mount_tag=${V9PTAG} "
fi

if [ -n "${ARGS}" ]; then
  qm set ${VMID} --args "${ARGS}"
  if [ $? -ne 0 ]; then
    echo "Set args failed"
    qm destroy ${VMID} --purge
    exit 1
  fi
fi

if [ -n "${VFSDIRID}" ]; then
  # pvesh create /cluster/mapping/dir --id "${VFSDIRID}" -map node=node1,path=/path/to/share1 --map node=node2,path=/path/to/share2
  qm set ${VMID} --virtiofs0 dirid=${VFSDIRID},cache=always,direct-io=1
fi

# 添加 128G 数据盘
qm set ${VMID} --scsi$((SATAIDX++)) ${STORAGE}:128
qm set ${VMID} --scsi$((SATAIDX++)) "${ISO_PATH},media=cdrom"
qm set "${VMID}" --boot "order=$(for i in $(seq 0 $((SATAIDX - 1))); do if [ ${i} -eq 0 ]; then echo -n "scsi${i}"; else echo -n ";scsi${i}"; fi; done)"

BRIDGE=$(awk -F: '/^iface vmbr/ {print $1}' /etc/network/interfaces | awk '{print $2}' | head -1)
if [ -z "${BRIDGE}" ]; then
  echo "Get bridge failed"
  qm destroy ${VMID} --purge
  exit 1
fi
qm set ${VMID} --net0 virtio,bridge=${BRIDGE}

qm set ${VMID} --serial0 socket
qm set ${VMID} --agent enabled=1
qm set ${VMID} --smbios1 "uuid=$(cat /proc/sys/kernel/random/uuid),manufacturer=$(echo -n "RROrg" | base64),product=$(echo -n "${TYPE}" | base64),version=$(echo -n "${ARCH:-x86_64}" | base64),base64=1"
qm set ${VMID} --onboot "${ONBOOT}"

echo "Created success, VMID=${VMID}"

exit 0
