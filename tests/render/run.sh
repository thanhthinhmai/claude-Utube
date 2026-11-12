#!/bin/sh
# Tests for tools/render (specs/019): wrapper flags, probe decisions, fingerprint, chunked recorder.
#   sh tests/render/run.sh
# The recorder tests open the library's headless browser (software GL) on a tiny 2D film; no GPU needed.
set -u
HERE=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
cd "$HERE" || exit 2
if node --test --test-reporter=spec tests/render/*.test.mjs; then echo "✓ tests/render: all passed"; exit 0
else echo "✗ tests/render: failures above"; exit 1; fi
