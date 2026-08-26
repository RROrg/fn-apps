#!/usr/bin/env bash
#
# Copyright (C) 2022 Ing <https://github.com/wjz304>
#
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#

fnos() {
  echo "Getting fnOS.json..."

  OLD="$(jq 'if type=="array" then . else [] end' "fnOS.json" 2>/dev/null || echo '[]')"
  OLD="${OLD:-[]}"
  NEW="[]"
  # x86_64
  FNNAS=("https://www.fnnas.com/download?key=fnos" "https://www.fnnas.com/download-arm")
  for url in "${FNNAS[@]}"; do
    DATAS=$(curl -sL "${url}" | grep -oP '{(?:[^{}]*fnos[^,]*[\.iso|\.img\.gz][^{}]*thunder|[^{}]*thunder[^{}]*fnos[^,]*[\.iso|\.img\.gz])[^}]*"}' | sort -u | sed 's/\\\"/"/g' | jq -s .)

    while IFS= read -r data; do
      echo "Processing ${data}"
      BASE=$(echo "${data}" | jq -r '.url')
      ARCH="$(echo "${BASE}" | awk -F'/' '{print $4}' | sed 's/.*/\L&/' | sed 's/^arm$/aarch64/; s/^x86$/x86_64/')"
      NAME=""
      VER=""
      if [ "${ARCH}" == "x86_64" ]; then
        NAME="fnOS-${ARCH}"
        VER="$(echo "${data}" | jq -r '.version')"
        if [ "${VER}" == "null" ]; then
          VER="$(echo "${BASE}" | sed -n 's/.*_\([0-9]\+\.[0-9]\+\.[0-9]\+\).*/\1/p')"
        fi
      fi
      if [ "${ARCH}" == "aarch64" ]; then
        NAME="$(echo "${data}" | jq -r '.name')"
        VER="$(echo "${BASE}" | awk -F'/' '{print $6}')"
      fi
      if [ -z "${NAME}" ] || [ -z "${VER}" ]; then
        continue
      fi
      URL="$(echo "${data}" | jq -r '.thunder' | sed 's/^thunder:\/\///' | base64 -d 2>/dev/null | sed 's/^AA//; s/ZZ$//')"
      HASH="$(echo "${data}" | jq -r '.hash')"
      # build compact JSON object (includes name) and add only if not present in OLD
      JSON=$(jq -n --arg arch "${ARCH}" --arg name "${NAME}" --arg ver "${VER}" --arg url "${URL}" --arg hash "${HASH}" '{arch:$arch,name:$name,version:$ver,url:$url,hash:$hash}' | jq -c .)

      if [ -z "${JSON}" ] || ! printf '%s' "${JSON}" | jq -e . >/dev/null 2>&1; then
        continue
      fi
      if printf '%s' "${OLD}" | jq -e --argjson obj "${JSON}" 'index($obj) | not' >/dev/null 2>&1; then
        NEW=$(printf '%s' "${NEW}" | jq -c --argjson obj "${JSON}" '. + [$obj]')
      fi
    done <<<"$(printf '%s' "${DATAS}" | jq -c '.[]')"
  done

  ALL=$(printf '%s' "${OLD}" "${NEW}" | jq -s '.[0] + .[1] | sort_by(.arch, .name, ([.version | scan("[0-9]+") | tonumber]), .version)')
  printf '%s' "${ALL}" | jq -S . >"fnOS.json"
}

fygonas() {
  echo "Getting FygoOS.json..."
  OLD="$(jq 'if type=="array" then . else [] end' "FygoOS.json" 2>/dev/null || echo '[]')"
  OLD="${OLD:-[]}"
  NEW="[]"
  # x86_64
  FNNAS=("https://fygonas.com/download")
  for url in "${FNNAS[@]}"; do
    DATAS=$(curl -sL "${url}" | grep -oP '{[^{}]*fygoos[^,]*[\.iso|\.img\.gz][^}]*"}' | sort -u | sed 's/\\\"/"/g' | jq -s .)

    while IFS= read -r data; do
      echo "Processing ${data}"
      BASE=$(echo "${data}" | jq -r '.url')
      ARCH="$(echo "${BASE}" | awk -F'/' '{print $4}' | sed 's/.*/\L&/' | sed 's/^arm$/aarch64/; s/^x86$/x86_64/')"
      NAME=""
      VER=""
      if [ "${ARCH}" == "x86_64" ]; then
        NAME="FygoOS-${ARCH}"
        VER="$(echo "${data}" | jq -r '.version')"
      fi
      if [ "${ARCH}" == "aarch64" ]; then
        NAME="$(echo "${data}" | jq -r '.name')"
        VER="$(echo "${BASE}" | awk -F'/' '{print $6}')"
        if [ "armsr" = "${VER}" ]; then
          VER="$(echo "${NAME}" | sed -n 's/.*_\([0-9]\+\.[0-9]\+\.[0-9]\+\).*/\1/p')"
        fi
      fi
      if [ -z "${NAME}" ] || [ -z "${VER}" ]; then
        continue
      fi
      URL="$(echo "${data}" | jq -r '.url')"
      HASH="$(echo "${data}" | jq -r '.hash')"
      # build compact JSON object (includes name) and add only if not present in OLD
      JSON=$(jq -n --arg arch "${ARCH}" --arg name "${NAME}" --arg ver "${VER}" --arg url "${URL}" --arg hash "${HASH}" '{arch:$arch,name:$name,version:$ver,url:$url,hash:$hash}' | jq -c .)

      if [ -z "${JSON}" ] || ! printf '%s' "${JSON}" | jq -e . >/dev/null 2>&1; then
        continue
      fi
      if printf '%s' "${OLD}" | jq -e --argjson obj "${JSON}" 'index($obj) | not' >/dev/null 2>&1; then
        NEW=$(printf '%s' "${NEW}" | jq -c --argjson obj "${JSON}" '. + [$obj]')
      fi
    done <<<"$(printf '%s' "${DATAS}" | jq -c '.[]')"
  done

  ALL=$(printf '%s' "${OLD}" "${NEW}" | jq -s '.[0] + .[1] | sort_by(.arch, .name, ([.version | scan("[0-9]+") | tonumber]), .version)')
  printf '%s' "${ALL}" | jq -S . >"FygoOS.json"
}

fnos
fygonas
