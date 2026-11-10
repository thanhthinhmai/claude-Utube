#!/bin/sh
# Test chấm kịch bản và đo phim (specs/010). Offline: phim mẫu tạo bằng ffmpeg vào tests/filmcheck/.tmp/.
#   sh tests/filmcheck/run.sh            (cần: python3, ffmpeg)
set -eu
HERE=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
PY=python3
[ -x "$HERE/tools/.venv/bin/python" ] && PY="$HERE/tools/.venv/bin/python"
command -v ffmpeg >/dev/null 2>&1 || { echo "✗ cần ffmpeg"; exit 1; }
rm -rf "$HERE/tests/filmcheck/.tmp" && mkdir -p "$HERE/tests/filmcheck/.tmp"
"$PY" -m unittest discover -s "$HERE/tests/filmcheck" -t "$HERE/tests/filmcheck" "$@"
