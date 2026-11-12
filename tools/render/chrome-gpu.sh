#!/bin/sh
# Browser wrapper for the library's PLAYWRIGHT_CHROME hook (specs/019, research R2/R3).
# Playwright launches it headless; it starts the full Chromium headful, off-screen, with the GPU flags, because on
# Linux/WSL2 the GPU is only reachable from a headful browser on the display (WSLg X11 → Mesa d3d12 → Windows GPU).
# Nothing in the library changes. Usage: PLAYWRIGHT_CHROME=<this file> node core/render/still.mjs …
HERE=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
LIB="${STUDIO_LIB:-$HERE/lib/lemo-opuscar}"
BROWSERS="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"
rev=$(sed -n '/"name": *"chromium"/,/revision/s/.*"revision": *"\([0-9]*\)".*/\1/p' "$LIB/node_modules/playwright-core/browsers.json" 2>/dev/null | head -1)
CHROME="${STUDIO_CHROMIUM:-$BROWSERS/chromium-$rev/chrome-linux64/chrome}"
if [ ! -x "$CHROME" ]; then
  echo "chrome-gpu.sh: full Chromium missing ($CHROME). Run: sh bin/studio deps gpu" >&2
  exit 127
fi
[ -d /usr/lib/wsl/lib ] && export LD_LIBRARY_PATH="/usr/lib/wsl/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export GALLIUM_DRIVER="${GALLIUM_DRIVER:-d3d12}"
for a in "$@"; do
  shift
  case "$a" in
    --headless*|--hide-scrollbars|--mute-audio|--blink-settings=primaryHoverType*) ;;
    *) set -- "$@" "$a" ;;
  esac
done
exec "$CHROME" --use-angle=gl --enable-gpu --ignore-gpu-blocklist --ozone-platform=x11 \
  --window-size=1920,1080 --window-position=-3000,-3000 \
  --disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows "$@"
