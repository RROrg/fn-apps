#!/usr/bin/env bash
#
# Copyright (C) 2022 Ing <https://github.com/wjz304>
#
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#

[ -n "${BASH_VERSION:-}" ] || exec bash "$0" "$@"
set -euo pipefail

SOCKET_PATH="${SOCKET_PATH:-/var/apps/fn-scheduler/target/fn-scheduler.sock}"
BASE_PATH="${BASE_PATH:-/app/fn-scheduler}"
TIMEOUT="${TIMEOUT:-8}"

usage() {
  cat <<'EOF'
Usage:
  $0 <api> [data|@file|-] [method]

Arguments:
  api        API path under /api, e.g. tasks, tasks/batch, health
  data       Optional JSON payload, @path/to/file.json, or - to read JSON from stdin
  method     Optional HTTP method. Default: POST when data is provided, otherwise GET

Environment:
  SOCKET_PATH  Unix socket path (default: /var/apps/fn-scheduler/target/fn-scheduler.sock)
  BASE_PATH    URL base path (default: /app/fn-scheduler)
  TIMEOUT      curl max-time in seconds (default: 8)

Examples:
  $0 health
  $0 tasks
  $0 tasks/batch '{"action":"stop","task_ids":[1]}'
  $0 settings @/tmp/settings.json PUT
  echo '{"name":"demo","account":"root"}' | $0 tasks - POST
  $0 tasks '{"name":"demo","account":"root"}' POST
EOF
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  usage
  exit 0
fi

API="${1:-}"
DATA="${2:-}"
METHOD="${3:-}"

if [[ -z ${API} ]]; then
  usage
  exit 1
fi
if [[ -z ${METHOD} ]]; then
  if [[ -n ${DATA} ]]; then
    METHOD="POST"
  else
    METHOD="GET"
  fi
else
  METHOD="$(echo "${METHOD}" | tr '[:lower:]' '[:upper:]')"
fi

if [[ ! -S ${SOCKET_PATH} ]]; then
  echo "socket not found: ${SOCKET_PATH}" >&2
  exit 2
fi

BASE_PATH="/${BASE_PATH#/}"
BASE_PATH="${BASE_PATH%/}"
URL="http://unix${BASE_PATH}/api/${API#/}"

cleanup_file=""
cleanup() {
  if [[ -n ${cleanup_file} && -f ${cleanup_file} ]]; then
    rm -f "${cleanup_file}"
  fi
}
trap cleanup EXIT

if [[ -n ${DATA} ]]; then
  data_args=()
  if [[ ${DATA} == @* ]]; then
    data_file="${DATA#@}"
    if [[ ! -f ${data_file} ]]; then
      echo "data file not found: ${data_file}" >&2
      exit 3
    fi
    cleanup_file="$(mktemp)"
    python3 - "${data_file}" "${cleanup_file}" <<'PY'
from pathlib import Path
import sys

src, dst = sys.argv[1:3]
content = Path(src).read_text(encoding="utf-8-sig")
Path(dst).write_text(content, encoding="utf-8")
PY
    data_args=(--data-binary "@${cleanup_file}")
  elif [[ ${DATA} == '-' ]]; then
    data_args=(--data-binary @-)
  else
    data_args=(--data-raw "${DATA}")
  fi

  curl_args=(
    -sS
    --max-time "${TIMEOUT}"
    --unix-socket "${SOCKET_PATH}"
    -H 'Content-Type: application/json'
    -X "${METHOD}"
    "${data_args[@]}"
    -i
    "${URL}"
  )
else
  curl_args=(
    -sS
    --max-time "${TIMEOUT}"
    --unix-socket "${SOCKET_PATH}"
    -X "${METHOD}"
    -i
    "${URL}"
  )
fi

curl "${curl_args[@]}"
echo
