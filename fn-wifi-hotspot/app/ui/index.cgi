#!/bin/bash

# ============================================================================
# File Name       : index.cgi
# Version         : 1.0.0
# Author          : FNOSP/xieguanru
# Collaborators   : FNOSP/MR_XIAOBO, RROrg/Ing
# Created         : 2025-11-18
# Last Modified   : 2026-01-14
# Description     : CGI script for serving static files.
# Usage           : Rename this file to index.cgi, place it under the application's /ui directory,
#                   and run `chmod +x index.cgi` to grant execute permission.
# License         : MIT
# ============================================================================

# 【注意】修改你自己的静态文件根目录，以本应用为例：
BASE_PATH="/var/apps/fn-wifi-hotspot/target/www"

# 1. 从 REQUEST_URI 里拿到 index.cgi 后面的路径
#    例如：/cgi/ThirdParty/fn-wifi-hotspot/index.cgi/index.html?foo=bar
#    先去掉 ? 后面的 query string
URI_NO_QUERY="${REQUEST_URI%%\?*}"

# 默认值 (如果没匹配到 index.cgi)
REL_PATH="/"

# 用 index.cgi 作为切割点，取后面的部分
case "$URI_NO_QUERY" in
  *index.cgi*)
    # 去掉前面所有直到 index.cgi 为止的内容，保留后面的
    # /cgi/ThirdParty/fn-wifi-hotspot/index.cgi/index.html -> /index.html
    REL_PATH="${URI_NO_QUERY#*index.cgi}"
    ;;
esac

# 如果为空或只有 /，就默认 /index.html
if [ -z "$REL_PATH" ] || [ "$REL_PATH" = "/" ]; then
  REL_PATH="/index.html"
fi

# 拼出真实文件路径: BASE_PATH + /ui + index.cgi 后面的路径
TARGET_FILE="${BASE_PATH}${REL_PATH}"

# 简单防御：禁止 .. 越级访问
if echo "$TARGET_FILE" | grep -q '\.\.'; then
  echo "Status: 400 Bad Request"
  echo "Content-Type: text/plain; charset=utf-8"
  echo ""
  echo "Bad Request: Path traversal detected"
  exit 0
fi

# 2. 判断文件是否存在
if [ ! -f "$TARGET_FILE" ]; then
  echo "Status: 404 Not Found"
  echo "Content-Type: text/plain; charset=utf-8"
  echo ""
  echo "404 Not Found: ${REL_PATH}"
  exit 0
fi

# 3. 根据扩展名简单判断 Content-Type
ext="${TARGET_FILE##*.}"
ext_lc="$(printf '%s' "$ext" | tr '[:upper:]' '[:lower:]')"

case "$ext_lc" in
  html | htm)
    mime="text/html; charset=utf-8"
    ;;
  css)
    mime="text/css; charset=utf-8"
    ;;
  js)
    mime="application/javascript; charset=utf-8"
    ;;
  cgi)
    mime="application/x-httpd-cgi"
    ;;
  jpg | jpeg)
    mime="image/jpeg"
    ;;
  png)
    mime="image/png"
    ;;
  gif)
    mime="image/gif"
    ;;
  svg)
    mime="image/svg+xml"
    ;;
  txt | log)
    mime="text/plain; charset=utf-8"
    ;;
  json)
    mime="application/json; charset=utf-8"
    ;;
  xml)
    mime="application/xml; charset=utf-8"
    ;;
  *)
    mime="application/octet-stream"
    ;;
esac

# 支持 If-Modified-Since 返回 304
mtime=0
if stat_cmd="$(command -v stat 2>/dev/null)" && [ -n "$stat_cmd" ]; then
  mtime=$(stat -c %Y "$TARGET_FILE" 2>/dev/null || echo 0)
  size=$(stat -c %s "$TARGET_FILE" 2>/dev/null || echo 0)
else
  # 回退：用 Python 获取
  size=$(python -c "import os,sys;print(os.path.getsize(sys.argv[1]))" "$TARGET_FILE" 2>/dev/null || echo 0)
  mtime=$(python -c "import os,sys;print(int(os.path.getmtime(sys.argv[1])))" "$TARGET_FILE" 2>/dev/null || echo 0)
fi

last_mod="$(date -u -d "@$mtime" +"%a, %d %b %Y %H:%M:%S GMT" 2>/dev/null || date -u -r "$TARGET_FILE" +"%a, %d %b %Y %H:%M:%S GMT" 2>/dev/null || echo "")"

if [ -n "${HTTP_IF_MODIFIED_SINCE:-}" ]; then
  ims_epoch=$(date -d "$HTTP_IF_MODIFIED_SINCE" +%s 2>/dev/null || echo 0)
  if [ "$ims_epoch" -ge "$mtime" ] && [ "$mtime" -gt 0 ]; then
    echo "Status: 304 Not Modified"
    echo ""
    exit 0
  fi
fi

# 4. 输出头
printf 'Content-Type: %s\r\n' "$mime"
printf 'Content-Length: %s\r\n' "$size"
printf 'Last-Modified: %s\r\n' "$last_mod"
printf '\r\n'

# 对于 HEAD 请求只返回头
if [ "${REQUEST_METHOD:-GET}" = "HEAD" ]; then
  exit 0
fi

cat "$TARGET_FILE"
