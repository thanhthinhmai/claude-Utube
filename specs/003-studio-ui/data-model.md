# Data Model: Giao diện và API của xưởng

Tất cả nằm trong `.studio/` (không vào git). Thời điểm theo ISO 8601 UTC.

## Job (`.studio/jobs/<id>.json`)

| Trường | Kiểu | Ràng buộc |
|---|---|---|
| `id` | string | `j-YYYYMMDD-HHMMSS-xxxx` |
| `owner` | string | giai đoạn 1: `"local"` |
| `kind` | enum | `learn` · `film` |
| `name` | string | 1–80 ký tự (tên bộ hoặc tên phim) |
| `status` | enum | `running` · `waiting_review` · `waiting_resume` · `done` · `failed` · `stopped` (lưu); `inactive` (tính khi đọc) |
| `step` | string | ≤ 120 ký tự, ví dụ "Đo video 3/5" |
| `progress` | object\|null | `{done: int ≥ 0, total: int ≥ 1}`, `done ≤ total` |
| `started_at`, `updated_at` | string | `updated_at ≥ started_at` |
| `log` | [{t, line}] | giữ 50 dòng cuối, mỗi dòng ≤ 300 ký tự |
| `links` | object | tuỳ chọn: `set`, `film`, `style` (mã tài nguyên) |
| `error` | string\|null | khi `failed` |
| `review_ids` | [string] | theo thứ tự tạo |

**Chuyển trạng thái**:

```
running ⇄ waiting_review (review request / decision)
running → done | failed | stopped
waiting_review → waiting_resume (đã có quyết định nhưng không còn lệnh wait nào trong 60 s)
waiting_resume → running (review wait nhận quyết định / job step)
running (updated_at cũ hơn 600 s) ⇒ hiển thị inactive
```

## Review (`.studio/reviews/<id>.json` + `<id>.decision.json`)

| Trường | Kiểu | Ràng buộc |
|---|---|---|
| `id` | string | `r-…` |
| `owner` | string | `"local"` |
| `job_id` | string | việc tồn tại |
| `kind` | enum | `style-1` · `style-2` |
| `created_at` | string | |
| `summary_md` | string | ≤ 200 KB; bản tóm tắt tiếng Việt (template `review-vi.md`). Với `style-2`: ghi chú của Claude về những gì số đo không bắt được (FR-006) |
| `set` | string | mã bộ tham chiếu |
| `compare` | object\|null | `style-2`: chép từ `proof/compare.json` (`luma_diff`, `sat_median_diff`, `dark_diff_pp`, `palette_matched`, `palette_needed`, `pass`, `round`, `ref`, `ours`) |
| `final_round` | bool | `style-2`: đã hết vòng sửa |
| `waiting` | object | `{last_poll_at}`, do `review wait` cập nhật mỗi lần hỏi |

**Decision** (`<id>.decision.json`, tạo độc quyền, không bao giờ sửa):

| Trường | Kiểu | Ràng buộc |
|---|---|---|
| `value` | enum | `approve` · `revise` · `accept_anyway` · `stop` |
| `note` | string | bắt buộc (≥ 3 ký tự) khi `revise`; ≤ 4000 ký tự |
| `source` | enum | `ui` · `chat` |
| `at` | string | |

`accept_anyway` và `stop` chỉ hợp lệ khi `kind = style-2` và `final_round = true`.

## ServerInfo (`.studio/server.json`)

`{pid, port, started_at, version}`, do `launcher` ghi và xoá.

## Tài nguyên đọc từ thư mục có sẵn

| Tài nguyên | Nguồn | Mã |
|---|---|---|
| Film | `films/<name>/` (`<name>.mp4`, `poster.jpg`, `<name>.srt`, `CREDITS`, `TREATMENT.md`) | `name` |
| ReferenceSet | `references/<set>/set.json`, `profile/summary.json`, `profile/v*/video.json`, `profile/v*/sheets/*.jpg`, `proof/out/*.jpg` | `set` |
| SavedStyle | `my-styles/<slug>/style.json`, `STYLE.md`, `EVIDENCE.md`, `styleframe.jpg` | `slug` |
