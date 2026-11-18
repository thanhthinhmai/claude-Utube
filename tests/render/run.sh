#!/bin/sh
# Tests for tools/render (specs/019): wrapper flags, probe decisions, fingerprint, chunked recorder.
# Also the pure parts of the styles' film kits (specs/022): my-styles/*/kit/test/*.test.mjs.
#   sh tests/render/run.sh
# The recorder tests open the library's headless browser (software GL) on a tiny 2D film; no GPU needed.
set -u
HERE=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
cd "$HERE" || exit 2
fail=0
node --test --test-reporter=spec tests/render/*.test.mjs || fail=1
# kit tests import 'three' by its bare name: the project root has no node_modules and ES modules ignore NODE_PATH,
# so a resolve hook maps it to the library's copy
kits=$(ls my-styles/*/kit/test/*.test.mjs 2>/dev/null)
if [ -n "$kits" ]; then
  # shellcheck disable=SC2086
  node --import ./tests/render/three-resolve.mjs --test --test-reporter=spec $kits || fail=1
fi
# the kit's sound (specs/023): numpy, scipy, the library's sampler and pluck, so the library's Python from its root
if [ -x lib/lemo-opuscar/.venv/bin/python ]; then
  (cd lib/lemo-opuscar && .venv/bin/python -m unittest discover -s "$HERE/tests/render" -p 'test_sound.py') || fail=1
else
  echo "! kit sound tests skipped: the library's Python is not installed (sh bin/studio deps music)"
fi
if [ "$fail" = 0 ]; then echo "✓ tests/render: all passed"; exit 0
else echo "✗ tests/render: failures above"; exit 1; fi
