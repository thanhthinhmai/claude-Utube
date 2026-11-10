# Contract: lệnh mới của `bin/studio`

Chạy được ở cả local và trong container (`STUDIO_MODE=online`, `STUDIO_JOB`). Ra màn hình bằng tiếng Anh, ngắn. `--json` in đúng một đối tượng JSON.

## `sh bin/studio script check <film> [--json]`

Chấm kịch bản bằng máy (R2), không mạng, không gọi Claude. Ghi `machine[]` vào `checks.json`.

| Mã thoát | Nghĩa |
|---|---|
| 0 | điểm ≥ 7 và mọi điều kiện cứng đạt |
| 1 | chưa đạt (in từng lỗi: `P02.1 long_sentence 31 words`) |
| 2 | không chạy được (thiếu tệp, sai định dạng phần đầu) |

**Điều kiện cứng**: `format` (phần đầu và số đoạn), `sources` (câu có số mà đoạn không có nguồn; đường dẫn chưa có trong `opened.json` với mã 2xx), `length` (thời lượng đọc ước tính trong ±15% `Target`), `unchanged` (R9, từ lượt sửa thứ hai).

**Điểm** (bắt đầu 10, tối thiểu 0):

| Luật | Trừ |
|---|---|
| `long_sentence`: câu > 25 từ (> 40 ký tự với zh, ja, ko) | 0,5 mỗi câu |
| `no_hook`: không có dấu hiệu hook trong cửa sổ đầu | 2 |
| `intro_opening`: câu đầu là câu chào hoặc giới thiệu kênh | 2 |
| `retention_gap`: khoảng giữa hai điểm giữ chân > 90 giây (phim ≥ 90 giây) | 1 mỗi khoảng |
| `cliche`: cụm sáo rỗng trong danh sách | 0,5 mỗi lần |
| `risky_number`: số dễ đọc sai viết bằng chữ số | 0,5 mỗi lần |
| `punctuation`: hơn 1 dấu ngoặc hoặc gạch ngang mỗi 100 từ | 0,5 |

## `sh bin/studio script review <film> [--json]`

Chạy biên tập (R3) khi `script check` đạt; chưa đạt thì thoát 1 và không gọi Claude. Lưu `.check/script-r<n>.md` và `review-r<n>.json`, ghi `editor[]` vào `checks.json`.

| Mã thoát | Nghĩa |
|---|---|
| 0 | đạt (≥ 8, không còn P1): `verdict = pass` |
| 1 | chưa đạt, còn vòng sửa: in lỗi P1/P2 theo đoạn |
| 3 | chưa đạt và đã hết 2 vòng sửa: `verdict = failed` (FR-010). Agent dừng; online, worker cho việc lỗi do xưởng |
| 2 | không chạy được (biên tập trả sai lược đồ hai lần liền: tính là một lượt không đạt, FR edge case) |

Lượt 1 là lượt chấm đầu; lượt 2 và 3 là sau vòng sửa 1 và 2. Vòng sửa theo yêu cầu của người giao phim (FR-019) mở thêm lượt, không tính vào giới hạn.

**Lược đồ trả lời của biên tập**:

```json
{"score": 0-10, "issues": [{"level": "P1|P2|P3", "para": "Pnn", "reason": "string ≤ 200 chars"}],
 "checked_sources": [{"url": "string", "matches": true}]}
```

## `sh bin/studio script status <film> [--json]`

In `verdict`, điểm cuối và số vòng sửa. Mã 0 khi `pass` hoặc `skipped`, 1 khi `pending`, 3 khi `failed`.

`sh bin/studio script skip <film> --reason "no narration"`: chỉ được khi thư mục phim không có `voices/` và không có `narration.json`. Ghi `verdict = skipped` (FR-003).

## `sh bin/studio web fetch <url> [--film <film>]`

Mở một trang (R4) và in chữ của trang (tối đa 20 000 ký tự), dòng đầu là `status <mã> <url cuối>`. Có `--film` thì ghi vào `.check/opened.json`.

- Local: tải thẳng, cùng giới hạn kích thước và loại nội dung.
- Online: `POST {STUDIO_PROXY}/internal/web/fetch` với `Authorization: Bearer <mã của việc>`, thân `{"url"}`. Proxy trả `{"status", "final_url", "content_type", "text"}`, hoặc `400 blocked_address` / `413 too_large` / `415 unsupported_type` / `429 fetch_limit` / `504 timeout`.

## `sh bin/studio qc <film> [--json]`

Đo phim cuối (FR-011, FR-012) và ghi `film` vào `checks.json` và `CHECKS.md`. Mã 0 đạt, 1 có lỗi (in từng lỗi kèm mốc giây), 2 không chạy được.

| Mục | Ngưỡng | Cần |
|---|---|---|
| `silence_ratio` | ≤ 0,20 trên khoảng từ từ đầu tới từ cuối | narration |
| `long_pause` | khoảng lặng ≥ 0,8 giây chỉ giữa hai đoạn `[Pnn]` khác nhau | narration |
| `cut_in_sentence` | không cắt cảnh trong câu; cắt ≥ min(0,4 giây, khoảng nghỉ) sau từ cuối của câu trước | narration |
| `key_shot` | cảnh có từ cuối của mỗi đoạn dài ≥ 2,5 giây | narration |
| `tail` | thời lượng phim − kết thúc từ cuối ≤ 1,5 giây | narration |
| `still` | không đoạn hình đứng im > 6 giây (`still_max` theo phong cách, R7) | mọi phim |
| `missing_glyph` | 0 ký tự không có phông | mọi phim |

## `sh bin/studio config editor-model <inherit|opus|sonnet|haiku>` (local)

Lưu vào `.studio/config.json` (R6). Online: Settings → General, trường `editor_model`.
