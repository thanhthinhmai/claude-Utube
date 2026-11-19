# Data Model: Điểm duyệt và chỉnh sửa trên trang việc làm phim

## Point (điểm duyệt)

Năm giá trị cố định: `script`, `voice`, `shots`, `mix`, `publish`.

| Điểm | Bước trên thanh | Tệp tính dấu | Phép kiểm phải đạt để duyệt | Cổng chặn |
|---|---|---|---|---|
| script | Script | `SCRIPT.md`, `SOURCES.md` | `script check` đạt | `voice make` |
| voice | Voice | `lines.json`, `voices/*` | `qc voice` đạt (gồm lời khớp kịch bản) | — |
| shots | Shots | dấu `all` của `tiers` (bỏ `mix.json`) | `qc plan` và `qc shots` đạt với dấu hiện tại; không còn cảnh báo phong cách chưa chấp nhận | `render-gate` |
| mix | Mix | `mix.json`, `out/mix.wav` | `out/mix.wav` mới hơn `mix.json` | — |
| publish | Publish | `publish/pack.json` | `publish --check-only` đạt | — |

## Film reviews (trong `checks.json` → `reviews`)

```json
"reviews": {
  "on": ["script", "shots"],
  "from": "channel night-questions",
  "approved": {
    "script": {"fingerprint": "a1b2…", "at": "2026-11-19T14:02:11Z", "by": "owner@…|local", "source": "ui|chat|api",
               "review_id": "r-…|null"},
    "shots": null
  },
  "skipped": {"voice": {"reason": "…", "at": "…"}}
}
```

- `on`: đặt khi `channel attach` (theo `channel.reviews`, mặc định `["script","shots"]`) hoặc bằng `point set`. Phim không có kênh thì lấy mặc định.
- Một lần duyệt **còn hiệu lực** khi `approved[p].fingerprint` bằng dấu hiện tại của điểm `p`.
- Trạng thái của một điểm: `off`, `not_reached`, `waiting` (có yêu cầu duyệt chưa có quyết định), `approved` (còn hiệu lực), `stale` (đã duyệt nhưng dấu đổi), `rejected` (quyết định cuối là `revise`), `skipped` (phim không có lời đọc, áp cho script và voice).
- Chỉ bật hay tắt được điểm ở trạng thái `off`, `not_reached`, `stale` hoặc `rejected`. Điểm `approved` hay `waiting` thì không.

## Channel (bổ sung)

- `reviews`: danh sách con của năm điểm. Thiếu thì coi là `["script","shots"]`. Đặt bằng `channel set <kênh> reviews script,shots` (`none` là không điểm nào).

## Step (bước) và đồ thị

Mười bước theo thứ tự: `Treatment, Script, Voice, Look, Picture, Shots, Mix, Render, Self-check, Publish`.

Phụ thuộc, dùng cho "Must run again" và "If you change this":

```text
Script  → Voice → Picture → Shots → Render → Self-check → Publish
Voice   → Mix → (mux) → Self-check → Publish
Look    → Picture
```

Trạng thái của một bước (`steps.status`): `done`, `running` (bước hiện tại của việc, hoặc khoá bận), `waiting` (điểm duyệt đang chờ), `todo`, `stale`, `skipped`. Cách tính `stale`:

| Bước | Là `stale` khi |
|---|---|
| Voice | có `voices/` nhưng `lines.json` không khớp `SCRIPT.md`, hoặc có dòng thiếu `wav` hay `wav` cũ hơn lần đổi chữ của dòng |
| Picture | kết quả `tiers.plan` có dấu khác dấu `all` hiện tại |
| Shots | kết quả `tiers.shots` có dấu khác dấu `all` hiện tại |
| Mix | `out/mix.wav` cũ hơn `mix.json`, `narration.json` hoặc một `voices/*.wav` |
| Render | kết quả `tiers.render` có dấu khác dấu `all`, hoặc video cũ hơn bản trộn (khi đó chỉ cần ghép tiếng lại) |
| Self-check | kết quả `tiers.final` có dấu khác dấu `all`, hoặc cũ hơn video |
| Publish | `publish` cũ hơn video, hoặc `pack.json` đổi sau lần kiểm |

`steps.impact(point)` trả danh sách bước sẽ phải làm lại nếu sửa điểm đó (cột "If you change this").

## Action (thao tác, tài liệu `action` trong sổ việc)

| Trường | Kiểu | Ghi chú |
|---|---|---|
| id | `a-YYYYMMDD-HHMMSS-xxxx` | |
| job_id, owner | chuỗi | quyền như việc |
| point | một trong năm điểm | |
| op | xem `contracts/cli.md` (`script-para`, `voice-say`, `voice-remake`, `voice-set`, `shot`, `shots-check`, `except`, `accept-style`, `mix`, `publish`) | |
| args | đối tượng | đã kiểm kiểu ở API |
| base | dấu 16 hex | dấu của điểm mà trang đang hiện |
| status | `queued` → `running` → `done` \| `failed` \| `conflict` \| `invalid` \| `busy` | theo mã thoát của `edit` |
| result | JSON do `edit --json` in | điểm, lỗi, ảnh mới, dấu mới |
| created_at, started_at, ended_at | ISO | |

Mỗi việc chạy thao tác lần lượt, theo thứ tự tạo. Mỗi lần đổi trạng thái thì ghi một dòng nhật ký việc, ví dụ `Edit script-para P3: score 8.5/10`.

## Review (bổ sung cho specs/003)

- `kind` thêm `script`, `voice`, `shots`, `mix`, `publish`; nhãn: "script review", "voice review", "shots review", "mix review", "publish review".
- `film`: tên phim (bắt buộc với năm loại này).
- Quyết định `approve` của năm loại này cần thêm `base` (dấu của điểm). Máy chủ gọi `points.approve(film_dir, point, base, source, by, review_id)`, và chỉ ghi quyết định khi lệnh đó đạt. `revise` cần ghi chú như hiện nay.

## Edit log (`.check/edits.jsonl`)

Mỗi dòng: `{"at", "by", "source": "ui|chat|api", "op", "point", "ref": "P3|L17|S012|mix|title", "old", "new", "result": "ok|check_failed", "stale": ["Voice", …]}`. Chỉ ghi khi thao tác đã lưu được.

## Busy lock (`.check/busy.json`)

`{"step": "Voice", "pid": 1234, "host": "…", "since": "…", "by": "edit|job run"}`. Cùng `host`: còn sống khi `pid` còn chạy và chưa quá 6 giờ. Khác `host` (online): còn sống khi chưa quá 6 giờ và việc đang `running` với bước trùng.
