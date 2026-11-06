# Contract: `sh bin/studio learn …` và `deps learn`

Mọi lệnh chạy bằng `tools/.venv/bin/python tools/style-learn/learn.py`, được gọi qua `bin/studio`. Chưa cài thì báo cách cài và thoát mã 1.

## `deps learn [--extra]`

Tạo hoặc cập nhật `tools/.venv`, cài `requirements-learn.txt`; với `--extra` cài thêm `requirements-learn-extra.txt`. Không động tới `lib/`. Mã thoát: 0 xong, 1 lỗi (thiếu Python ≥ 3.11 và không có uv, mạng…).

## `learn fetch <set> (--channel URL [--count N] | --videos URL… | --files PATH…) [--max-seconds S] [--deny TÊN…]`

- Tạo `references/<set>/`, tải hoặc chép video vào `videos/`, ghi `set.json`.
- `--count`: mặc định 12, 3–30.
- Trước khi tải: in số video, nguồn, và lời nhắc về quyền sử dụng (FR-001a).
- Nền tảng bị chặn hoặc thiếu yt-dlp: mã 1 kèm hướng dẫn đặt file vào `references/<set>/videos/` rồi chạy `--files`.
- Chạy lại thì bỏ qua video đã có.

## `learn measure <set> [--only vNN…]`

Đo mọi video `fetched` (hoặc đã đổi `source_sig`) và ghi `profile/<id>/`. In tiến độ (khung/giây). Video lỗi → `skipped` kèm lý do, các video khác vẫn đo. Mã 0 nếu ≥ 1 video đo được.

## `learn transcribe <set> [--model small] [--lang auto]`

Chép lời các video `measured`, ghi `profile/<id>/words.json` và cập nhật `speech`. Thiếu faster-whisper: mã 1 kèm cách cài (`deps learn --extra`).

## `learn summary <set>`

Ghi `profile/summary.json` và `profile/summary.md` (bảng dễ đọc). Không cần mạng.

## `learn check-names <set> <file>…`

Mã 0 khi sạch; mã 1 kèm `file:dòng: "<chuỗi>" (lý do)` cho mỗi vi phạm.

## `learn compare <set> --ref <ảnh-gốc> --ours <ảnh-tự-vẽ> [--round N]`

Ghi `proof/compare.json` và `proof/compare.jpg` (trái: gốc, phải: tự vẽ, dưới: bảng chỉ số). Mã 0 khi `pass`, 1 khi chưa đạt.

## `learn save <set> --slug S --en "Name" [--cn "名"] --based-on SLUG`

Kiểm tra slug, chạy lại `check-names` trên mọi file trong `style/`, chép gói vào `my-styles/<slug>/`, thêm dòng vào `my-styles/README.md`. Từ chối (mã 1) nếu slug trùng, có vi phạm tên, hoặc gói chứa file media hay bản chép lời.

## `learn clean <set> [--keep]`

Không có `--keep`: xoá `videos/`, `profile/*/words.json`, `profile/*/sheets/`, `proof/compare.jpg` và mọi ảnh trong `proof/out/` không phải ảnh tự vẽ (`ours_*`, ví dụ khung gốc `ref.jpg`) của bộ `<set>`; giữ `set.json` (đã bỏ `origin`, `title`) và số liệu. Chỉ xoá trong `references/<set>/`. In danh sách và dung lượng đã xoá.
