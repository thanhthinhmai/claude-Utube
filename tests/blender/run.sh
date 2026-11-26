#!/bin/sh
# Test of the Blender engine (specs/038): shot plan, local runs with a fake Blender, resume, GPU guard, estimate, uses.
#   sh tests/blender/run.sh       (needs: python3, ffmpeg, node)
set -eu
HERE=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
PY=python3
[ -x "$HERE/tools/.venv/bin/python" ] && PY="$HERE/tools/.venv/bin/python"
command -v ffmpeg >/dev/null 2>&1 || { echo "✗ cần ffmpeg"; exit 1; }
"$PY" -m unittest discover -s "$HERE/tests/blender" -t "$HERE/tests/blender" "$@"
