# Contract: tích hợp với skill và luồng làm phim

## Skill `style-learn`

| Bước của skill | Thêm |
|---|---|
| 0 (sau khi chốt tên bộ) | `JOB=$(sh bin/studio job start --kind learn --name <set> --set <set> \| head -1)`; in đường link giao diện cho người dùng |
| 1 | `job step $JOB "Tải video" …`; lệnh dài bọc bằng `job run $JOB --step "Đo video" -- sh bin/studio learn measure <set>` (và `transcribe`) |
| 2–5 | `job step` ở đầu mỗi bước |
| 6 (duyệt 1) | ghi tóm tắt vào `references/<set>/style/review-1.md`; `RID=$(sh bin/studio review request $JOB --kind style-1 --set <set> --summary references/<set>/style/review-1.md \| head -1)`; báo người dùng: "Duyệt trên giao diện (link) hoặc bấm Esc rồi trả lời ở đây"; lặp `sh bin/studio review wait $RID` tới khi mã 0 |
| 6 (người dùng trả lời trong khung chat) | `sh bin/studio review decide $RID --value … --note "…" --source chat` |
| 6 (`revise`) | sửa theo `note`, tạo yêu cầu **mới** `style-1` |
| 8 (duyệt 2) | như bước 6 với `--kind style-2`; thêm `--final-round` khi đã dùng hết 2 vòng sửa; `accept_anyway` → `save --accept-proof`; `stop` → `job stop $JOB` |
| 10 | `job done $JOB --style <slug>` |
| Lỗi không tự sửa được | `job fail $JOB "<lỗi>"` |

## Luồng làm phim (`CLAUDE.md`)

- Bắt đầu: `job start --kind film --name <tên> --film <tên>` và in link.
- Mỗi giai đoạn (treatment, look, giọng, nhạc, hình, mix, render): `job step`.
- Render và các lệnh dài: bọc bằng `job run`.
- Xong: `job done --film <tên>`. Storyboard (nếu người dùng yêu cầu) vẫn duyệt trong khung chat ở MVP.

Khi `deps ui` chưa cài: các lệnh `job` và `review` báo một dòng và thoát mã 1. Skill **không dừng** vì vậy: bỏ qua phần ghi việc và duyệt trong khung chat như cũ.
