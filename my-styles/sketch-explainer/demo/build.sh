#!/bin/sh
# Rebuild the Sketch Explainer demo film. Writes only to $OUT (default: ../demo-out next to this folder).
set -e
LIB=/home/thinhmt/claude-Utube/lib/lemo-opuscar
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${OUT:-$(cd "$HERE/.." && pwd)/demo-out}
export LIB OUT
[ -f "$LIB/core/render/video.mjs" ] || { echo "set LIB (top of this file) to the lemo-opuscar library folder"; exit 1; }
P="$OUT/page"
mkdir -p "$P/voices"
cp "$HERE/index.html" "$HERE/plan.json" "$HERE/mix.py" "$HERE/lines.json" "$P/"
rm -rf "$P/kit" && cp -r "$HERE/../kit" "$P/kit"                     # the page reaches only its own folder
cd "$LIB"
if [ ! -f "$P/voices/dur.json" ]; then                                 # Kokoro am_michael; "say" replaces the text where set
  .venv/bin/python -c "import json,sys; r=json.load(open(sys.argv[1])); json.dump([dict(x, text=x.get('say', x['text'])) for x in r], open(sys.argv[2], 'w'))" "$HERE/lines.json" "$P/voices/say.json"
  .venv/bin/python core/tts/tts.py "$P/voices/say.json" "$P/voices"
fi
# PLAYWRIGHT_CHROME=<studio>/tools/render/chrome-gpu.sh renders on the GPU (WSL2/Linux); without it, software rendering
node core/render/video.mjs "$P" --fps 30 --out "$OUT/video.mp4"
.venv/bin/python "$P/mix.py"                                          # piano bed, effects, voice → $P/out/mix.wav
sh core/render/mux.sh "$OUT/video.mp4" "$P/out/mix.wav" "$OUT/sketch-demo.mp4" 30 1
echo "→ $OUT/sketch-demo.mp4"
