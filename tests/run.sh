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
echo jpg-a > "$U/styles/a/poster.jpg"
printf '#!/bin/sh\necho "LEMO_HOME=$LEMO_OPUSCAR_HOME ARGS=$*"\n' > "$U/plugin/skills/lemo-opuscar/scripts/setup.sh"
$G -C "$U" init -q && $G -C "$U" add -A && $G -C "$U" commit -qm c1
C1=$(git -C "$U" rev-parse HEAD)
mkdir -p "$U/styles/b"; echo b > "$U/styles/b/STYLE.md"; echo jpg-b > "$U/styles/b/poster.jpg"
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
check "máy mới có poster (004)" [ -f "$L/styles/a/poster.jpg" ]
check "máy mới báo đã có poster" has "đã có poster: 1/1"

# Máy cài trước 004: danh sách sparse cũ, chưa có poster
old_install() {
  printf '%s\n' '/*' '!/styles/*/demo/' '!/styleboard/' '!/docs/frames/' '!/docs/cover.jpg' '!/docs/opuscar98.jpg' '!/styles/*/poster.jpg' \
    > "$L/.git/info/sparse-checkout"
  git -C "$L" sparse-checkout reapply 2>/dev/null
}
old_install
check "giả máy cũ: không có poster" [ ! -e "$L/styles/a/poster.jpg" ]
INODE=$(ls -di "$L/.git" | cut -d' ' -f1)
run setup
check "máy cũ: setup mã 0" rc_is 0
check "máy cũ: nhận poster" [ -f "$L/styles/a/poster.jpg" ]
check "máy cũ: không tải lại thư viện" [ "$(ls -di "$L/.git" | cut -d' ' -f1)" = "$INODE" ]
check "máy cũ: vẫn không có demo" [ ! -e "$L/styles/a/demo" ]
check "thư viện không bị sửa (SC-007)" [ -z "$(git -C "$L" status --porcelain)" ]
run setup
check "đã có poster: chạy lại không tải gì" sh -c '! printf "%s" "$1" | grep -q "tải poster"' _ "$OUT"
# setup bị ngắt giữa chừng: danh sách mới đã ghi nhưng chưa reapply → vẫn thiếu poster
old_install
printf '%s\n' '/*' '!/styles/*/demo/' '!/styleboard/' '!/docs/frames/' '!/docs/cover.jpg' '!/docs/opuscar98.jpg' \
  > "$L/.git/info/sparse-checkout"
check "giả setup bị ngắt: danh sách mới, chưa có poster" [ ! -e "$L/styles/a/poster.jpg" ]
run setup
check "danh sách mới mà thiếu poster: setup tải lại" has "đã có poster: 1/1"
check "danh sách mới mà thiếu poster: có poster" [ -f "$L/styles/a/poster.jpg" ]

# Tải poster lỗi: git giả hỏng ở bước sparse-checkout
REALGIT=$(command -v git)
printf '#!/bin/sh\ncase " $* " in *" sparse-checkout "*) echo "fatal: unable to access" >&2; exit 128 ;; esac\nexec "%s" "$@"\n' "$REALGIT" > "$FAKE/git"
chmod +x "$FAKE/git"
old_install
run setup
check "poster lỗi: setup vẫn mã 0" rc_is 0
check "poster lỗi: báo chưa tải được" has "poster chưa tải được"
check "poster lỗi: thư viện vẫn dùng được" [ -f "$L/styles/a/STYLE.md" ]
mv "$L" "$W/lib-saved"
run setup
check "poster lỗi ở lần cài đầu: mã 0, thư viện có" sh -c '[ "$1" -eq 0 ] && [ -f "$2/styles/a/STYLE.md" ]' _ "$RC" "$L"
check "poster lỗi ở lần cài đầu: báo chưa tải được" has "poster chưa tải được"
rm -rf "$L"; mv "$W/lib-saved" "$L"
rm -f "$FAKE/git"
run setup
check "có mạng lại: setup lấy được poster" [ -f "$L/styles/a/poster.jpg" ]

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
check "đếm poster = 2" has '"library_posters":2'
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

echo "== trình duyệt chạy ngầm (thư viện hệ thống, Linux)"
if [ "$(uname -s)" = Linux ]; then
  run status --json
  check "chưa cài deps → không có dòng browser" sh -c '! printf "%s" "$1" | grep -q "\"name\":\"browser\""' _ "$OUT"
  mkdir -p "$L/node_modules/playwright-core" "$W/.cache/ms-playwright/chromium_headless_shell-1/chrome-linux"
  printf '#!/bin/sh\n' > "$W/.cache/ms-playwright/chromium_headless_shell-1/chrome-linux/headless_shell"
  chmod +x "$W/.cache/ms-playwright/chromium_headless_shell-1/chrome-linux/headless_shell"
  printf '#!/bin/sh\necho "\tlibnss3.so => not found"\necho "\tlibc.so.6 => /lib/libc.so.6"\n' > "$FAKE/ldd"; chmod +x "$FAKE/ldd"
  run status --json
  check "thiếu libnss3 → browser missing, chưa sẵn sàng" has '"name":"browser","found":"","min":"libs","state":"missing"'
  check "gợi ý lệnh apt-get kèm tên thư viện thiếu" has 'libnss3.so → Ubuntu/WSL: sudo apt-get install -y libnss3'
  check "thiếu thư viện → mã 1" rc_is 1
  printf '#!/bin/sh\necho "\tlibc.so.6 => /lib/libc.so.6"\n' > "$FAKE/ldd"
  run status --json
  check "đủ thư viện → browser ok, sẵn sàng" has '"name":"browser","found":"ok","min":"libs","state":"ok"'
  check "đủ thư viện → mã 0" rc_is 0
  rm -rf "$L/node_modules" "$W/.cache" "$FAKE/ldd"
fi

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

echo "== env.sh của bản đóng gói (016)"
echo 'echo envsh-loaded >&2' > "$P/env.sh"
run help
check "có env.sh thì nạp" has "envsh-loaded"
rm -f "$P/env.sh"
mv "$L/.git" "$W/libgit"
run status
check "không có .git: thư viện không do xưởng quản lý" has "không phải thư viện do xưởng quản lý"
echo 0.1.0 > "$P/.core-version"
run status
check "bản đóng gói: thư viện đúng phiên bản dù không có git" has "đúng phiên bản"
rm -f "$P/.core-version"; mv "$W/libgit" "$L/.git"
run help
check "không có env.sh thì bỏ qua" sh -c '! printf "%s" "$1" | grep -q envsh-loaded' _ "$OUT"

echo
echo "PASS $PASS/$((PASS + FAIL))"
[ "$FAIL" -eq 0 ]
