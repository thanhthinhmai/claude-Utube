#!/bin/sh
# Test giao diện và API của xưởng (offline). Cần: sh bin/studio deps ui
set -eu
HERE=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
PY="$HERE/tools/.venv/bin/python"
"$PY" -c 'import fastapi, httpx' 2>/dev/null || { echo "✗ chưa cài: sh bin/studio deps ui"; exit 1; }
"$PY" -m unittest discover -s "$HERE/tests/ui" -t "$HERE/tests/ui" "$@"
# the desktop shell's logic (specs/015): plain Node, no Electron needed
if command -v node >/dev/null 2>&1; then
  node --test "$HERE"/desktop/test/*.test.js
else
  echo "- desktop tests skipped: no node"
fi
