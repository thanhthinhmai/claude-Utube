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
if [ "$fail" = 0 ]; then echo "✓ tests/render: all passed"; exit 0
else echo "✗ tests/render: failures above"; exit 1; fi
