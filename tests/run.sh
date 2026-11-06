#!/bin/sh
# Test cho bin/studio. Chạy offline: thư viện giả là một repo git cục bộ, công cụ giả nằm trong PATH riêng.
#   sh tests/run.sh
set -u

HERE=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd -P)
W=$(mktemp -d "${TMPDIR:-/tmp}/studio test.XXXXXX")     # dấu cách trong đường dẫn là cố ý
trap 'rm -rf "$W"' EXIT
REALPY=$(command -v python3 || true)
G="git -c user.name=t -c user.email=t@t -c init.defaultBranch=main"
PASS=0; FAIL=0

check() {  # check "mô tả" lệnh…
  d=$1; shift
  if "$@"; then PASS=$((PASS + 1)); echo "ok   $d"; else FAIL=$((FAIL + 1)); echo "FAIL $d"; printf '%s\n' "$OUT" | sed 's/^/     | /'; fi
}
has() { printf '%s' "$OUT" | grep -q -- "$1"; }
rc_is() { [ "$RC" -eq "$1" ]; }

# ---------- PATH riêng: chỉ công cụ hệ thống cần thiết + công cụ giả ----------
SYS="$W/sysbin"; FAKE="$W/fakebin"; mkdir -p "$SYS" "$FAKE"
for t in git sh sed awk grep head ls mkdir rmdir rm mv cat dirname basename tr env cp ln touch wc cut sort find chmod uname mktemp date readlink expr id; do
  p=$(command -v "$t" 2>/dev/null) && ln -s "$p" "$SYS/$t"
done
fake() {  # fake tên "dòng phiên bản"  (rỗng = xoá)
  rm -f "$FAKE/$1"
  if [ -n "$2" ]; then printf '#!/bin/sh\necho "%s"\n' "$2" > "$FAKE/$1"; chmod +x "$FAKE/$1"; fi
}
tools_ok() {
  fake node "v22.1.0"; fake ffmpeg "ffmpeg version 7.1 Copyright (c) 2000-2024"; fake python3 "Python 3.12.1"; fake uv ""
}

# ---------- thư viện giả với 2 commit ----------
U="$W/upstream lib"
mkdir -p "$U/core/render" "$U/styles/a/demo" "$U/styles/_template" "$U/plugin/skills/lemo-opuscar/scripts"
echo agents > "$U/AGENTS.md"; echo r > "$U/core/render/video.mjs"; echo '{}' > "$U/package-lock.json"
echo a > "$U/styles/a/STYLE.md"; echo demo > "$U/styles/a/demo/x.js"; echo tpl > "$U/styles/_template/STYLE.md"
printf '#!/bin/sh\necho "LEMO_HOME=$LEMO_OPUSCAR_HOME ARGS=$*"\n' > "$U/plugin/skills/lemo-opuscar/scripts/setup.sh"
$G -C "$U" init -q && $G -C "$U" add -A && $G -C "$U" commit -qm c1
C1=$(git -C "$U" rev-parse HEAD)
mkdir -p "$U/styles/b"; echo b > "$U/styles/b/STYLE.md"
$G -C "$U" add -A && $G -C "$U" commit -qm c2
C2=$(git -C "$U" rev-parse HEAD)

# ---------- dự án thử ----------
P="$W/my project"; mkdir -p "$P/bin" "$P/films" "$P/references" "$P/my-styles"
cp "$HERE/bin/studio" "$P/bin/studio"; cp "$HERE/library.lock" "$HERE/.gitignore" "$P/"
cp "$HERE/films/README.md" "$P/films/"; cp "$HERE/references/README.md" "$P/references/"
$G -C "$P" init -q && $G -C "$P" add -A && $G -C "$P" commit -qm init
L="$P/lib/lemo-opuscar"

COMMIT=$C1
run() {  # run [thư mục] lệnh-con…  → OUT, RC
  dir=$P; if [ -d "$1" ]; then dir=$1; shift; fi
  OUT=$(cd "$dir" && env -i HOME="$W" PATH="$FAKE:$SYS" STUDIO_LIB_REPO="$U" STUDIO_LIB_COMMIT="$COMMIT" /bin/sh "$P/bin/studio" "$@" 2>&1)
  RC=$?
}
json_ok() { [ -z "$REALPY" ] || printf '%s' "$OUT" | "$REALPY" -m json.tool >/dev/null; }

echo "== US1: setup"
tools_ok
run setup
check "tải mới → mã 0" rc_is 0
check "thư viện đúng commit C1" [ "$(git -C "$L" rev-parse HEAD 2>/dev/null)" = "$C1" ]
check "có styles/a/STYLE.md" [ -f "$L/styles/a/STYLE.md" ]
check "sparse: không có styles/a/demo" [ ! -e "$L/styles/a/demo" ]
check "đánh dấu studio.managed" [ "$(git -C "$L" config --get studio.managed)" = true ]
check "không đặt lemo.managed" [ -z "$(git -C "$L" config --get lemo.managed || true)" ]
check "không còn thư mục tạm" [ ! -e "$P/lib/.lemo-opuscar.tmp" ]
check "báo sẵn sàng" has "xưởng sẵn sàng"

mv "$U" "$U.off"
run setup
check "chạy lại không cần mạng → mã 0" rc_is 0
check "chạy lại báo đã đúng phiên bản" has "đã đúng phiên bản"
mv "$U.off" "$U"

COMMIT=$C2
run setup
check "nâng phiên bản → mã 0" rc_is 0
check "thư viện lên C2" [ "$(git -C "$L" rev-parse HEAD)" = "$C2" ]
check "có styles/b sau khi nâng" [ -f "$L/styles/b/STYLE.md" ]

echo x >> "$L/AGENTS.md"
run setup
check "thư viện bị sửa → setup mã 1" rc_is 1
check "thư viện bị sửa → báo thay đổi cục bộ" has "thay đổi cục bộ"
check "thư viện bị sửa → không ghi đè" grep -q x "$L/AGENTS.md"
git -C "$L" checkout -q -- .

echo '{"x":1}' > "$L/package-lock.json"
run setup
check "chỉ package-lock.json đổi → vẫn mã 0" rc_is 0
git -C "$L" checkout -q -- .

mv "$L" "$W/lib-saved"; mkdir -p "$L"; echo mine > "$L/notes.txt"
run setup
check "thư mục lạ → mã 1" rc_is 1
check "thư mục lạ → không xoá" [ -f "$L/notes.txt" ]
rm -rf "$L"; mv "$W/lib-saved" "$L"

fake node ""; fake ffmpeg "ffmpeg version 6.1.1-3ubuntu5 Copyright (c) 2000-2023"
run setup
check "thiếu node, ffmpeg 6.1 → mã 1" rc_is 1
check "liệt kê node thiếu" has "node .*thiếu"
check "liệt kê ffmpeg quá cũ kèm 6.1 và cần ≥ 7" has "ffmpeg  6.1 .*cần ≥ 7 .*quá cũ"
check "không tự cài: không có node mới" [ ! -e "$FAKE/node" ]
tools_ok

fake ffmpeg "ffmpeg version N-113345-gabcdef1 Copyright (c) 2000-2024 the FFmpeg developers"
run status --json
check "ffmpeg bản build theo ngày → unknown" has '"name":"ffmpeg","found":"","min":"7","state":"unknown"'
check "unknown không chặn sẵn sàng" has '"ready":true'
tools_ok

fake python3 "Python 3.9.18"; fake uv "uv 0.5.0"
run status --json
check "Python 3.9 + uv → ok" has '"name":"python","found":"3.9","min":"3.11","state":"ok"'
fake uv ""
run status --json
check "Python 3.9 không có uv → old" has '"name":"python","found":"3.9","min":"3.11","state":"old"'
tools_ok

COMMIT=abc
run setup
check "LIB_COMMIT sai → mã 2" rc_is 2
COMMIT=$C2

mv "$L" "$W/lib-saved"; mv "$U" "$U.off"
run setup
check "lần đầu mất mạng → mã 1" rc_is 1
check "lần đầu mất mạng → không để lại thư viện dở" [ ! -e "$L" ] && [ ! -e "$P/lib/.lemo-opuscar.tmp" ]
mv "$U.off" "$U"; mv "$W/lib-saved" "$L"

echo "== US2: status"
run status --json
check "sẵn sàng → mã 0" rc_is 0
check "JSON hợp lệ" json_ok
check "đếm phong cách thư viện = 2 (bỏ _template)" has '"library_styles":2'
check "đếm phong cách riêng = 0, phim = 0" has '"my_styles":0,"films":0'
mkdir -p "$P/my-styles/night" "$P/films/coffee"; echo s > "$P/my-styles/night/STYLE.md"
run status --json
check "đếm phong cách riêng = 1, phim = 1" has '"my_styles":1,"films":1'
run "$P/films" status
check "chạy từ thư mục con → mã 0" rc_is 0
check "bảng dễ đọc có dòng sẵn sàng" has "✓ sẵn sàng"
check "status không sửa thư viện (SC-006)" [ -z "$(git -C "$L" status --porcelain --untracked-files=no)" ]
echo y >> "$L/AGENTS.md"
run status --json
check "thư viện bị sửa → mã 1" rc_is 1
check "thư viện bị sửa → state modified" has '"state":"modified"'
git -C "$L" checkout -q -- .
mv "$U" "$U.off"
run status
check "status chạy offline" rc_is 0
mv "$U.off" "$U"

echo "== gitignore (SC-005)"
echo v > "$P/films/coffee/out.mp4"; echo v > "$P/references/clip.mp4"; echo v > "$P/references/notes.txt"
ST=$(git -C "$P" status --porcelain --untracked-files=all)
OUT=$ST
check "phim, video tham chiếu, thư viện không vào git" sh -c '! printf "%s" "$1" | grep -qE "films/coffee|references/|lib/"' _ "$ST"
check "phong cách riêng vẫn vào git" has "my-styles/night/STYLE.md"

echo "== deps, help"
run deps voice
check "deps chuyển LEMO_OPUSCAR_HOME đúng thư viện" has "LEMO_HOME=$L ARGS=deps voice"
run help
check "help → mã 0" rc_is 0
run bogus
check "lệnh lạ → mã 2" rc_is 2

echo
echo "PASS $PASS/$((PASS + FAIL))"
[ "$FAIL" -eq 0 ]
