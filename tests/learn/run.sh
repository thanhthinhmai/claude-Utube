#!/bin/sh
# Test công cụ học phong cách. Offline: video tổng hợp được tạo một lần vào thư mục tạm.
#   sh tests/learn/run.sh            (cần: sh bin/studio deps learn)
set -eu
HERE=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
PY="$HERE/tools/.venv/bin/python"
[ -x "$PY" ] || { echo "✗ chưa cài: sh bin/studio deps learn"; exit 1; }
FX=$(mktemp -d "${TMPDIR:-/tmp}/learn fixtures.XXXXXX")
trap 'rm -rf "$FX"' EXIT
echo "… tạo video tổng hợp"
"$PY" "$HERE/tests/learn/make_fixtures.py" "$FX"
LEARN_FIXTURES="$FX" "$PY" -m unittest discover -s "$HERE/tests/learn" -t "$HERE/tests/learn" "$@"
