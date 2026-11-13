#!/bin/sh
# Rebuild the Dusk Hypothetical demo film. Writes only to $OUT (default: ../demo-out next to this folder).
set -e
LIB=/home/thinhmt/claude-Utube/lib/lemo-opuscar
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${OUT:-$(cd "$HERE/.." && pwd)/demo-out}
export LIB OUT
[ -f "$LIB/core/render/video.mjs" ] || { echo "set LIB (top of this file) to the lemo-opuscar library folder"; exit 1; }
mkdir -p "$OUT/voices"
cd "$LIB"
[ -f "$OUT/voices/dur.json" ] || .venv/bin/python core/tts/tts.py "$HERE/lines.json" "$OUT/voices"   # Kokoro am_michael x1.1
# PLAYWRIGHT_CHROME=<studio>/tools/render/chrome-gpu.sh renders on the GPU (WSL2/Linux); without it, software WebGL
node core/render/video.mjs "$HERE" --fps 30 --out "$OUT/video.mp4"
VOICES="$OUT/voices" .venv/bin/python "$HERE/mix.py"                                                 # bed, foley, voice → $OUT/mix.wav
sh core/render/mux.sh "$OUT/video.mp4" "$OUT/mix.wav" "$OUT/dusk-demo.mp4" 30 0
echo "→ $OUT/dusk-demo.mp4"
