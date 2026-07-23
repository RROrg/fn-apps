#!/usr/bin/env bash
#
# Copyright (C) 2022 Ing <https://github.com/wjz304>
#
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#

WORKDIR="$(
  cd "$(dirname "$0")"
  pwd
)"

V=$(curl -sIL "https://github.com/ventoy/PXE/releases/latest" -o /dev/null -w '%{url_effective}' | grep -oP 'tag/v\K[\d.]+')
if [ -z "${V}" ]; then
  echo "ERROR: Failed to get latest iVentoy version"
  exit 1
fi
echo "iVentoy version: ${V}"

download_iventoy() {
  local ARCH="$1"
  local SUFF="$2"
  local URL="https://github.com/ventoy/PXE/releases/download/v${V}/iventoy-${V}-linux-${ARCH}-${SUFF}.tar.gz"
  local DEST="${WORKDIR}/app/server/${ARCH}"

  echo "Downloading ${URL} ..."
  curl -skL "${URL}" -o "iventoy-linux-${ARCH}.tar.gz"
  if [ $? -ne 0 ]; then
    echo "ERROR: Failed to download iVentoy for ${ARCH}"
    return 1
  fi

  echo "Extracting ${ARCH} ..."
  tar -xzf "iventoy-linux-${ARCH}.tar.gz" -C "."
  if [ $? -ne 0 ]; then
    echo "ERROR: Failed to extract iVentoy for ${ARCH}"
    rm -f "iventoy-linux-${ARCH}.tar.gz"
    return 1
  fi
  rm -f "iventoy-linux-${ARCH}.tar.gz"

  local EXTRACTED=$(find . -maxdepth 1 -type d -name "iventoy-*" | head -1)
  if [ -z "${EXTRACTED}" ]; then
    echo "ERROR: iVentoy directory not found in extracted archive for ${ARCH}"
    return 1
  fi

  mv -f "${EXTRACTED}" "${DEST}"
  rm -rf "${DEST}/{iso,log}" 2>/dev/null
  mv -f "${DEST}/data" "${DEST}/data.orig"
  mv -f "${DEST}/user" "${DEST}/user.orig"
  chmod +x "${DEST}/iventoy.sh" "${DEST}/lib/iventoy" 2>/dev/null || true

  echo "iVentoy ${ARCH} extracted successfully"
  return 0
}

rm -rf "${WORKDIR}/app/server"
mkdir -p "${WORKDIR}/app/server" >/dev/null 2>&1 || true

download_iventoy "x86_64" "free"
download_iventoy "arm64" "trial"

sed -i "s/^\(version.*= \).*$/\1${V}/" "${WORKDIR}/manifest"

echo "Done"
