#!/bin/sh
# Test máy chủ license của app desktop (specs/017). Offline; GitHub là máy chủ giả. Cần: sh bin/studio deps online
set -eu
HERE=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
PY="$HERE/tools/.venv/bin/python"
"$PY" -c 'import fastapi, httpx, argon2, cryptography' 2>/dev/null || { echo "✗ chưa cài: sh bin/studio deps online"; exit 1; }
"$PY" -m unittest discover -s "$HERE/tests/license" -t "$HERE/tests/license" "$@"
