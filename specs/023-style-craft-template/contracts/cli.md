# Contract: lệnh mới và lệnh được sửa

Mã thoát theo quy ước của xưởng: 0 đạt, 1 có lỗi cần sửa, 2 sai cách gọi, 3 thiếu công cụ hoặc dữ liệu.

## Học phong cách (`sh bin/studio learn …`, venv `tools/.venv`)

| Lệnh | Việc | Ghi ra |
|---|---|---|
| `learn refetch <set> --videos <URL…>` | tải lại và ghép với `vNN` cũ theo độ dài (≤ 1 s) và 5 khung giữa cảnh (ΔE ≤ 12). URL không ghép được thì báo và bỏ qua (mã 1). In lời nhắc bản quyền như `fetch` | `videos/vNN.mp4`, `set.json → url` |
| `learn craft <set> [--only vNN] [--strips 80]` | đo máy, cử động bên trong, chuyển cảnh cho từng cảnh (research R2, R3); cắt dải 8 khung cho các cảnh mẫu | `profile/<v>/craft.json`, `profile/<v>/strips/` |
| `learn sound <set> [--only vNN]` | nhịp đọc, nhạc, tiếng động (R5, R6). Cần `learn transcribe` trước (mã 3 nếu thiếu mốc từ) | `profile/<v>/sound.json` |
| `learn beats <set> --check` | kiểm `profile/beats.json` (data-model.md) | — |
| `learn craft-summary <set>` | gom số theo cỡ cảnh, theo nhịp và toàn bộ; in bảng | `profile/craft-summary.json` |
| `learn evidence <set> <vNN> <giây> --name <tên>` | trích một khung 640 px làm bằng chứng (video phải còn) | `profile/<v>/evidence/<tên>.jpg` |
| `learn template-check <slug>` | kiểm `TEMPLATE.md`, `template.json` và nhãn luật của `STYLE.md` (contracts/template-format.md). In từng chỗ thiếu: mục, dòng, lý do | — |
| `learn pairs <set> --batch <1-4> --component <tên> --ours <ảnh…> --ref <bằng chứng…> [--clip <mp4 của bộ dựng> --ref-strip <vNN/strips/Sxxx.jpg> --ref-measure <khoá>]` | bảng so: ≥ 3 cặp ảnh; với thành phần có chuyển động thì thêm đoạn mp4 hai nửa, kèm số đo hai bên. Dưới 3 cặp thì mã 2 | `pairs/<đợt>/<thành phần>.jpg`, `.mp4` |
| `learn clean <set>` | (đã có) xoá video và âm thanh. Chạy khi học xong, kể cả khi dừng hay lỗi | — |

`check-names` (đã có) được gọi thêm trên `TEMPLATE.md`, `template.json`, `kit/REVIEW.md`.

## Làm phim (`sh bin/studio …`)

| Lệnh | Việc |
|---|---|
| `voice make <phim>` | viết `voices/.say.json` (thay `text` bằng `say` ở dòng có `say`), gọi `tts.py` của thư viện, ra `voices/<id>.wav` và `voices/dur.json` như cũ. Bọc được trong `job run … --step "Voice"` |
| `qc voice <phim>` (sửa) | thêm luật `mispronounced`: từ nghe được khác chữ của dòng (sau khi gập dấu, so theo `asr` nếu có), báo mã dòng, chữ đúng, chữ nghe được, cách sửa "thêm `say` cho dòng <id>" |
| `qc shots <phim>` (sửa) | chụp thêm 4 khung/cảnh vào `.check/shots/motion/`. Luật `still_person` (chặn): cảnh có người mà tỉ lệ khối cử động < `template.json → motion.person_active_share_min`, báo mã cảnh, thời điểm, "thêm `act`, `move` hoặc `talk`". Luật cảnh báo phong cách `style_depth`: `focused_share` của cảnh ngoài khoảng của cỡ cảnh đó |
| `qc <phim>` (sửa, tầng 4) | thêm cảnh báo phong cách `style_still_ratio`, `style_motion720`, `style_person_motion`, `style_transitions` theo `template.json`; chấp nhận bằng `qc accept-style` như cũ |
| `page clip <phim> --from <s> --to <s> [--size WxH]` | ghi một đoạn ngắn (≤ 10 s) của trang phim bằng bộ ghi của specs/019, dùng GPU, cho bảng so. Ra `films/<phim>/.check/clips/<from>-<to>.mp4` |

Các luật mới chỉ chạy khi phong cách của phim có `template.json`. Phong cách không có template thì bỏ qua, ghi `skipped: no template`.

Luật cần numpy gọi `tools/.venv/bin/python`. Thiếu venv thì luật đó báo lỗi mã 3 "cần `sh bin/studio deps learn`", không cho qua.
