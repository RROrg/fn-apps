#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "${PYTHON_BIN:-}" ]; then
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN=python3
    elif command -v python >/dev/null 2>&1; then
        PYTHON_BIN=python
    else
        echo "Python is required but not found" >&2
        exit 1
    fi
fi

DB_PATH=${SCHEDULER_DB_PATH:-${SCRIPT_DIR}/scheduler.db}

ipv6_enabled=0
if [[ -n "${SCHEDULER_ENABLE_IPV6:-}" ]]; then
    shopt -s nocasematch
    case "${SCHEDULER_ENABLE_IPV6}" in
        1|true|yes|on) ipv6_enabled=1 ;;
    esac
    shopt -u nocasematch
fi

ssl_enabled=0
if [[ -n "${SCHEDULER_ENABLE_SSL:-}" ]]; then
    shopt -s nocasematch
    case "${SCHEDULER_ENABLE_SSL}" in
        1|true|yes|on) ssl_enabled=1 ;;
    esac
    shopt -u nocasematch
fi

if [[ -n "${SCHEDULER_HOST:-}" ]]; then
    HOST=${SCHEDULER_HOST}
else
    if [[ "${ipv6_enabled}" == "1" ]]; then
        HOST="::"
    else
        HOST="0.0.0.0"
    fi
fi

PORT=${SCHEDULER_PORT:-28256}

cmd=("${PYTHON_BIN}" "${SCRIPT_DIR}/scheduler_service.py" --host "${HOST}" --port "${PORT}" --db "${DB_PATH}")

ssl_cert=${SCHEDULER_SSL_CERT:-}
ssl_key=${SCHEDULER_SSL_KEY:-}

if [[ -n "${ssl_cert}" || -n "${ssl_key}" ]]; then
    if [[ -z "${ssl_cert}" || -z "${ssl_key}" ]]; then
        echo "SCHEDULER_SSL_CERT 与 SCHEDULER_SSL_KEY 需同时设置以启用 HTTPS" >&2
        exit 1
    fi
    cmd+=(--ssl-cert "${ssl_cert}" --ssl-key "${ssl_key}")
fi

if [[ -n "${SCHEDULER_BASE_PATH:-}" ]]; then
    cmd+=(--base-path "${SCHEDULER_BASE_PATH}")
fi

if [[ -n "${SCHEDULER_AUTH:-}" ]]; then
    cmd+=(--auth "${SCHEDULER_AUTH}")
fi

if [[ "${ipv6_enabled}" == "1" ]]; then
    cmd+=(--ipv6)
fi

if [[ "${ssl_enabled}" == "1" ]]; then
    cmd+=(--ssl)
fi

exec "${cmd[@]}"
