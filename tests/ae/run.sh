#!/bin/sh
# Test of the After Effects engine (specs/031): film.json, bundles, frame-exact splice, ae uses, CLI with a fake AE.
#   sh tests/ae/run.sh            (needs: python3, ffmpeg, node)
set -eu
HERE=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
PY=python3
[ -x "$HERE/tools/.venv/bin/python" ] && PY="$HERE/tools/.venv/bin/python"
command -v ffmpeg >/dev/null 2>&1 || { echo "✗ cần ffmpeg"; exit 1; }
"$PY" -m unittest discover -s "$HERE/tests/ae" -t "$HERE/tests/ae" "$@"
