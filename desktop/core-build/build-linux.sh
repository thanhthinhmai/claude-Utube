#!/bin/sh
# Build the Linux core for the Windows app (specs/016 R1):
#   sh desktop/core-build/build-linux.sh <version> [out-dir]
# Needs Docker. Writes claude-utube-core-linux-x64-<version>.tar.gz and core-manifest.json.
set -eu
ver=${1:?usage: build-linux.sh <version> [out-dir]}
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${2:-$root/dist/core/linux}
mkdir -p "$out"
file="claude-utube-core-linux-x64-$ver.tar.gz"
tag="claude-utube-core:$ver"

echo "↓ building the image (first time is slow)…"
git -C "$root" archive --format=tar HEAD | docker build -f deploy/core.Dockerfile --build-arg "CORE_VERSION=$ver" -t "$tag" -

cid=$(docker create "$tag")
trap 'docker rm -f "$cid" >/dev/null 2>&1 || true' EXIT
echo "↓ exporting the Linux…"
docker export "$cid" > "$out/core.tar"
unpacked=$(wc -c < "$out/core.tar" | tr -d ' ')
gzip -6 -c "$out/core.tar" > "$out/$file"
rm -f "$out/core.tar"

bytes=$(wc -c < "$out/$file" | tr -d ' ')
sum=$(sha256sum "$out/$file" | cut -d' ' -f1)
lib=$(sed -n 's/^LIB_COMMIT=//p' "$root/library.lock" | tr -d '\r' | head -n 1)
printf '{"version": "%s", "os": "linux-x64", "file": "%s", "sha256": "%s", "bytes": %s, "unpacked_bytes": %s, "lib_commit": "%s", "built": "%s"}\n' \
  "$ver" "$file" "$sum" "$bytes" "$unpacked" "$lib" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$out/core-manifest.json"
echo "✓ $out/$file ($((bytes / 1048576)) MB, unpacked $((unpacked / 1048576)) MB)"
limit=$((1900 * 1048576))
[ "$bytes" -le "$limit" ] || { echo "✗ larger than 1.9 GB" >&2; exit 1; }
