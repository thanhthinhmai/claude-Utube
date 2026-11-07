#!/bin/sh
# Bài chạy thật với Claude (specs/007 T048): TỐN TIỀN. Cần deploy/.env có khoá thật và DOMAIN=localhost.
#   sh tests/online/live.sh [--videos <thư mục có ≤ 3 video của bạn>] [--films 3] [--seconds 30] [--no-up]
set -eu
HERE=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
[ -f "$HERE/deploy/.env" ] || { echo "✗ chưa có deploy/.env (chép deploy/.env.example rồi điền)"; exit 1; }
grep -q '^DOMAIN=localhost$' "$HERE/deploy/.env" || { echo "✗ bài chạy thật dùng DOMAIN=localhost trong deploy/.env"; exit 1; }
echo "Bài này gọi Claude thật: 3 phim 30 giây và 1 lần học, ước khoảng 5–20 USD (trần mỗi việc trong cài đặt: 5 USD)."
printf "Gõ yes để chạy: "
read -r ok
[ "$ok" = yes ] || { echo "= đã huỷ"; exit 1; }
exec python3 "$HERE/tests/online/live.py" "$@"
