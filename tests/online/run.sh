#!/bin/sh
# Test chế độ online của xưởng (specs/007). Offline, không gọi Claude thật. Cần: sh bin/studio deps online
set -eu
HERE=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
PY="$HERE/tools/.venv/bin/python"
"$PY" -c 'import fastapi, httpx, argon2' 2>/dev/null || { echo "✗ chưa cài: sh bin/studio deps online"; exit 1; }
"$PY" -m unittest discover -s "$HERE/tests/online" -t "$HERE/tests/online" "$@"
