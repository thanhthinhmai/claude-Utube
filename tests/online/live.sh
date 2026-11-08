#!/bin/sh
# Bài chạy thật với Claude (specs/007 T048, specs/008 T035): dùng hạn mức gói Claude của bạn (và tiền nếu đi qua
# khoá API dự phòng). Cần deploy/.env với DOMAIN=localhost; khoá API không bắt buộc.
#   sh tests/online/live.sh [--videos <thư mục có ≤ 3 video của bạn>] [--films 3] [--seconds 30] [--no-up]
set -eu
HERE=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
[ -f "$HERE/deploy/.env" ] || { echo "✗ chưa có deploy/.env (chép deploy/.env.example rồi điền)"; exit 1; }
grep -q '^DOMAIN=localhost$' "$HERE/deploy/.env" || { echo "✗ bài chạy thật dùng DOMAIN=localhost trong deploy/.env"; exit 1; }
echo "Bài này gọi Claude thật: 3 phim 30 giây (và 1 lần học nếu có --videos). Nó dùng nhiều hạn mức gói Claude"
echo "của tài khoản đăng nhập trên AI accounts; gói Pro có thể chạm hạn mức 5 giờ. Trần mỗi việc: theo Settings → General."
printf "Gõ yes để chạy: "
read -r ok
[ "$ok" = yes ] || { echo "= đã huỷ"; exit 1; }
exec python3 "$HERE/tests/online/live.py" "$@"
