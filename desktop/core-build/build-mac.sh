#!/bin/sh
# Build the macOS core (Apple chip) for the desktop app (specs/016 research R2):
#   sh desktop/core-build/build-mac.sh <version> [out-dir]
# Runs on an arm64 Mac (GitHub's macos-14). Every download is pinned with its SHA-256. No venv here: the app makes
# tools/.venv and lib/lemo-opuscar/.venv with --system-site-packages when it installs the core.
set -eu
ver=${1:?usage: build-mac.sh <version> [out-dir]}
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${2:-$root/dist/core/mac}
[ "$(uname -s)-$(uname -m)" = Darwin-arm64 ] || { echo "✗ needs an Apple-chip Mac" >&2; exit 1; }

PY_URL=https://github.com/astral-sh/python-build-standalone/releases/download/20261026/cpython-3.12.16+20261026-aarch64-apple-darwin-install_only.tar.gz
PY_SHA=fbf4afef53c2a6b72bb741bc06d5671a9dfaf87bd84e5aa73ac9b3d0d589f14e
NODE_URL=https://nodejs.org/dist/v22.12.0/node-v22.12.0-darwin-arm64.tar.gz
NODE_SHA=293dcc6c2408da21562d135b0412525e381bb6fe150d688edb58fe850d0f3e13
FF=https://github.com/eugeneware/ffmpeg-static/releases/download/b6.0
FFMPEG_SHA=6be74d6f449889c2e87a75873894f8520cad56c08ac76f2a628d85b0519daaca
FFPROBE_SHA=a4db76bafdb8529312e138fb55aaf143cad21b6d672e2634c9dd07ae83c6a310
FFLIC_SHA=cb48bf09a11f5fb576cddb0431c8f5ed0a60157a9ec942adffc13907cbe083f2

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
C="$work/core"
mkdir -p "$C" "$out"
get() {  # get URL SHA FILE
  curl -fsSL --retry 3 -o "$3" "$1"
  echo "$2  $3" | shasum -a 256 -c - >/dev/null || { echo "✗ SHA-256 does not match: $1" >&2; exit 1; }
}

echo "↓ Python, Node, FFmpeg…"
get "$PY_URL" "$PY_SHA" "$work/py.tgz" && tar -xzf "$work/py.tgz" -C "$C"            # → core/python/
get "$NODE_URL" "$NODE_SHA" "$work/node.tgz" && mkdir -p "$C/node" && tar -xzf "$work/node.tgz" -C "$C/node" --strip-components 1
mkdir -p "$C/ffmpeg"
get "$FF/ffmpeg-darwin-arm64.gz" "$FFMPEG_SHA" "$work/ffmpeg.gz" && gunzip -c "$work/ffmpeg.gz" > "$C/ffmpeg/ffmpeg"
get "$FF/ffprobe-darwin-arm64.gz" "$FFPROBE_SHA" "$work/ffprobe.gz" && gunzip -c "$work/ffprobe.gz" > "$C/ffmpeg/ffprobe"
get "$FF/darwin-arm64.LICENSE" "$FFLIC_SHA" "$C/ffmpeg/LICENSE"
chmod +x "$C/ffmpeg/ffmpeg" "$C/ffmpeg/ffprobe"

echo "↓ the studio and its library…"
git -C "$root" archive --format=tar HEAD | tar -xf - -C "$C"
cat > "$C/env.sh" <<'ENV'
# Read by bin/studio in the packaged macOS core (specs/016): the bundled Node, FFmpeg and Python come first.
PATH="$ROOT/node/bin:$ROOT/ffmpeg:$ROOT/python/bin:$PATH"; export PATH
PLAYWRIGHT_BROWSERS_PATH="$ROOT/ms-playwright"; export PLAYWRIGHT_BROWSERS_PATH
ENV
export PATH="$C/node/bin:$C/ffmpeg:$C/python/bin:$PATH" PLAYWRIGHT_BROWSERS_PATH="$C/ms-playwright"
(cd "$C" && sh bin/studio setup) || true
[ -f "$C/lib/lemo-opuscar/AGENTS.md" ] || { echo "✗ the library did not download" >&2; exit 1; }

echo "↓ packages…"
PY="$C/python/bin/python3"
"$PY" -m pip install --quiet --disable-pip-version-check --no-warn-script-location \
  -r "$C/lib/lemo-opuscar/requirements.txt" -r "$C/lib/lemo-opuscar/requirements-voice.txt" \
  -r "$C/lib/lemo-opuscar/requirements-music.txt" \
  -r "$C/tools/requirements-ui.txt" -r "$C/tools/requirements-online.txt" \
  -r "$C/tools/requirements-learn.txt" -r "$C/tools/requirements-learn-extra.txt"
(cd "$C/lib/lemo-opuscar" && npm install --no-audit --no-fund --loglevel=error)
(cd "$C/lib/lemo-opuscar" && git checkout -- package-lock.json 2>/dev/null) || true
(cd "$C/lib/lemo-opuscar" && node node_modules/playwright-core/cli.js install chromium-headless-shell)

echo "↓ cleaning…"
rm -f "$C"/lib/lemo-opuscar/core/tts/*.onnx "$C"/lib/lemo-opuscar/core/tts/*.bin
find "$C" -name __pycache__ -type d -prune -exec rm -rf {} +
echo "$ver" > "$C/.core-version"

file="claude-utube-core-darwin-arm64-$ver.tar.gz"
unpacked=$(( $(du -sk "$C" | cut -f1) * 1024 ))
tar -czf "$out/$file" -C "$C" .
bytes=$(wc -c < "$out/$file" | tr -d ' ')
sum=$(shasum -a 256 "$out/$file" | cut -d' ' -f1)
lib=$(sed -n 's/^LIB_COMMIT=//p' "$root/library.lock" | tr -d '\r' | head -n 1)
printf '{"version": "%s", "os": "darwin-arm64", "file": "%s", "sha256": "%s", "bytes": %s, "unpacked_bytes": %s, "lib_commit": "%s", "built": "%s"}\n' \
  "$ver" "$file" "$sum" "$bytes" "$unpacked" "$lib" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$out/core-manifest.json"
echo "✓ $out/$file ($((bytes / 1048576)) MB, unpacked $((unpacked / 1048576)) MB)"
[ "$bytes" -le $((1900 * 1048576)) ] || { echo "✗ larger than 1.9 GB" >&2; exit 1; }
