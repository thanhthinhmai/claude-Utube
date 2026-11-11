#!/bin/sh
# Check a built core (specs/016 T009). Run from the core's studio folder:
#   sh smoke-core.sh            (Linux: inside the core container; macOS: in core-<ver>/)
# Checks: app check, app start, health, first owner, app stop, and that the sandbox blocks writes
# outside the job folder while 127.0.0.1 still works (SC-006).
set -eu
say() { echo "smoke: $*"; }
fail() { echo "smoke: ✗ $*" >&2; exit 1; }
# The packaged macOS core puts its own Node and FFmpeg first in PATH (bin/studio reads the same file)
if [ -f env.sh ]; then ROOT=$(pwd); . ./env.sh; fi
data=$(mktemp -d)
work=$(mktemp -d)
trap 'sh bin/studio app stop --force --data "$data" >/dev/null 2>&1 || true' EXIT

sh bin/studio app check --json --data "$data" > "$work/check.json"
grep -q '"ok": true' "$work/check.json" || { cat "$work/check.json"; fail "app check"; }
say "app check ok"

out=$(sh bin/studio app start --data "$data")
url=$(printf '%s\n' "$out" | sed -n 's/^URL: //p' | tail -n 1)
[ -n "$url" ] || { printf '%s\n' "$out"; fail "app start printed no URL"; }
say "app start ok ($url)"

i=0
until curl -fsS "$url/api/v1/health" >/dev/null 2>&1; do
  i=$((i + 1)); [ $i -lt 60 ] || fail "health"; sleep 1
done
say "health ok"

curl -fsS -X POST -H 'Content-Type: application/json' -H 'X-Studio: 1' \
  -d '{"email":"owner@example.com","password":"smoke-test-password-1"}' "$url/api/v1/auth/setup" >/dev/null \
  || fail "first owner"
say "first owner ok"

# Sandbox: the job folder can be written, the home folder cannot, 127.0.0.1 still answers
port=${url##*:}
case $(uname -s) in
  Linux)
    command -v bwrap >/dev/null && command -v socat >/dev/null || fail "bwrap or socat missing"
    bwrap --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp --bind "$work" "$work" \
      sh -c "echo ok > '$work/in' && ! (echo bad > '$HOME/smoke-out') 2>/dev/null && curl -fsS http://127.0.0.1:$port/api/v1/health >/dev/null" \
      || fail "bwrap sandbox"
    ;;
  Darwin)
    sandbox-exec -p "(version 1)(allow default)(deny file-write* (subpath \"$HOME\"))(allow file-write* (subpath \"$work\") (subpath \"$(cd "$work" && pwd -P)\"))" \
      sh -c "echo ok > '$work/in' && ! (echo bad > '$HOME/smoke-out') 2>/dev/null && curl -fsS http://127.0.0.1:$port/api/v1/health >/dev/null" \
      || fail "sandbox-exec"
    ;;
esac
[ -f "$work/in" ] && [ ! -e "$HOME/smoke-out" ] || fail "sandbox let a write through"
say "sandbox ok"

sh bin/studio app stop --data "$data" >/dev/null || fail "app stop"
say "app stop ok"

# The renderer's browser starts (Chromium headless shell from Playwright)
(cd lib/lemo-opuscar && node -e "require('playwright-core').chromium.launch().then(b => b.close())") || fail "chromium"
say "chromium ok"

# SMOKE_VOICE=1: the setup's model steps (contracts/release.md 5–6), then one spoken line checked by Whisper
if [ "${SMOKE_VOICE:-}" = 1 ]; then
  sh lib/lemo-opuscar/tools/fetch.sh voice >/dev/null || fail "fetch voice"
  sh bin/studio app models || fail "app models"
  printf '[{"id": "a", "text": "The quick brown fox jumps over the lazy dog."}]' > "$work/lines.json"
  lib/lemo-opuscar/.venv/bin/python lib/lemo-opuscar/core/tts/tts.py "$work/lines.json" "$work/voice" || fail "kokoro"
  [ -s "$work/voice/a.wav" ] || fail "no wav"
  lib/lemo-opuscar/.venv/bin/python lib/lemo-opuscar/core/tts/asr_check.py "$work/lines.json" "$work/voice" --lang en || fail "whisper"
  say "voice ok"
fi
say "all ok"
