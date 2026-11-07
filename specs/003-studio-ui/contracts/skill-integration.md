# Contract: tích hợp với skill và luồng làm phim

## Skill `style-learn`

| Bước của skill | Thêm |
|---|---|
| 0 (sau khi chốt tên bộ) | `JOB=$(sh bin/studio job start --kind learn --name <set> --set <set> \| head -1)`; in đường link giao diện cho người dùng |
| 1 | `job step $JOB "Fetch videos" …`; lệnh dài bọc bằng `job run $JOB --step "Measure videos" -- sh bin/studio learn measure <set>` (và `transcribe`) |
| 2–5 | `job step` ở đầu mỗi bước |
| 6 (duyệt 1) | ghi tóm tắt vào `references/<set>/style/review-1.md`; `RID=$(sh bin/studio review request $JOB --kind style-1 --set <set> --summary references/<set>/style/review-1.md \| head -1)`; báo người dùng: "Duyệt trên giao diện (link) hoặc bấm Esc rồi trả lời ở đây"; lặp `sh bin/studio review wait $RID` tới khi mã 0 |
| 6 (người dùng trả lời trong khung chat) | `sh bin/studio review decide $RID --value … --note "…" --source chat` |
| 6 (`revise`) | sửa theo `note`, tạo yêu cầu **mới** `style-1` |
| 8 (duyệt 2) | như bước 6 với `--kind style-2`; thêm `--final-round` khi đã dùng hết 2 vòng sửa; `accept_anyway` → `save --accept-proof`; `stop` → `job stop $JOB` |
| 10 | `job done $JOB --style <slug>` |
| Lỗi không tự sửa được | `job fail $JOB "<lỗi>"` |

## Luồng làm phim (`CLAUDE.md`)

- Bắt đầu: `job start --kind film --name <tên> --film <tên>` và in link.
- Mỗi giai đoạn: `job step` với tên trong danh sách chuẩn (mục dưới).
- Render và các lệnh dài: bọc bằng `job run`.
- Xong: `job done --film <tên>`. Storyboard (nếu người dùng yêu cầu) vẫn duyệt trong khung chat ở MVP.

Khi `deps ui` chưa cài: các lệnh `job` và `review` báo một dòng và thoát mã 1. Skill **không dừng** vì vậy: bỏ qua phần ghi việc và duyệt trong khung chat như cũ.

## Chữ trên trang Jobs (005)

Bước và nhật ký bằng tiếng Anh, khớp phần còn lại của giao diện.

**Dòng xưởng tự ghi:**

| Lúc | Bước hiện tại | Dòng nhật ký |
|---|---|---|
| Bắt đầu việc | `Starting` | `Job started` |
| Gửi yêu cầu duyệt lần n | `Waiting for review n` | `Review n requested` |
| Có quyết định | | `Review n: <Approve \| Request changes \| Accept anyway \| Stop> (via UI \| via chat)[: <ghi chú>]` |
| Tiếp tục sau duyệt | (bước Claude ghi tiếp) | `Resumed after review n: <quyết định>` |
| `job run` kết thúc | | `(command exited with code N)` |
| Kết thúc | `Done` · `Failed` · `Stopped` | `Failed`: nội dung lỗi Claude ghi bằng `job fail`, giữ nguyên |

**Tên bước Claude ghi:**
- Làm phim: `Treatment`, `Look`, `Storyboard`, `Voice`, `Music`, `Picture`, `Mix`, `Render`, `Self-check`.
- Học phong cách: `Fetch videos`, `Measure videos`, `Transcribe`, `Summarize`, `Report measurements`, `Analysis (3 agents)`, `Cross-check`, `Write style`, `Proof frame round <n>`, `Save style`.

Xưởng không ép danh sách; đây là chỉ dẫn. Không đổi: tóm tắt duyệt (ngôn ngữ người dùng), thông báo terminal, dòng lệnh con in ra, việc cũ đã lưu.
