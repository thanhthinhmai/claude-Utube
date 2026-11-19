# Contract: API v1 (bổ sung)

Quyền giống `GET /jobs/{id}` (specs/025): local thì mọi người dùng của máy; online và app thì chủ việc hoặc chủ xưởng, người khác nhận `404 not_found`. Mã API (specs/009) gọi được các đường này qua cơ chế hiện có (`tokens.is_forbidden`), không thêm phạm vi quyền. Mọi lỗi theo dạng hiện có `{"error": {"code", "message"}}`.

## `GET /api/v1/jobs/{id}/steps`

Trả trạng thái để vẽ thanh tiến trình và các khung sửa.

```json
{
  "film": "what-if-you-never-slept",
  "steps": [{"name": "Script", "state": "done|running|waiting|todo|stale|skipped", "note": "Approved 14:02", "point": "script"}],
  "points": {"script": {"on": true, "state": "approved", "fingerprint": "a1b2…", "approved_at": "…", "by": "…"}},
  "impact": {"script": ["Voice", "Picture", "Shots", "Mix", "Render", "Self-check", "Publish"],
             "voice": ["Picture", "Shots", "Mix", "Render", "Self-check", "Publish"],
             "shots": ["Render", "Self-check", "Publish"], "mix": ["Self-check", "Publish"], "publish": []},
  "busy": {"step": "Voice", "since": "…"} ,
  "editable": {"shots": true, "reason": null},
  "catalog": {"sets": ["bedroom", "…", "custom:platform"], "cams": ["wide", "…"], "acts": ["yawn", "…"], "act_prefixes": {"face": ["…"]}},
  "voices": ["am_michael", "…"],
  "mix_ranges": {"under": [-11.5, -0.3], "duck": [-20, 0], "sfx": [-24, 6], "music": ["seed:7", "seed:3", "seed:11", "none"], "current": {…}, "defaults": {…}},
  "review": {"id": "r-…", "kind": "shots", "decision": null}
}
```

- `editable.shots` là `false` khi phim không có `scenes.json`. Khi đó `reason` có giá trị `"no scene table"` hoặc `"style has no kit"`.
- Có `ETag` theo các dấu nội dung. Trang gọi lại khi nhận sự kiện `job.updated`.

## `POST /api/v1/jobs/{id}/actions`

Body: `{"point": "script", "op": "script-para", "args": {"para": "P3", "text": "…"}, "base": "a1b2…"}`.

- Kiểm kiểu và độ dài ở API (`422 invalid`). `op` phải thuộc `point`. Việc phải là việc phim chưa kết thúc (`409 finished`).
- Trả `202 {"id": "a-…", "status": "queued"}`. Thao tác chạy theo R12.
- Gửi quá 30 thao tác mỗi phút cho một việc thì nhận `429`.

## `GET /api/v1/jobs/{id}/actions/{aid}`

Trả tài liệu `action` (data-model), có `status` và `result`. Trang theo dõi kết quả bằng sự kiện `job.updated`, rồi đọc lại tài liệu này.

## `PUT /api/v1/jobs/{id}/points`

Body: `{"on": ["script", "shots", "voice"]}`. Gọi thẳng `points.set_on` (local và online: chỉ ghi `checks.json`, không cần container). Đổi một điểm đang `approved` hay `waiting` thì nhận `409 point_locked`.

## `POST /api/v1/reviews/{rid}/decision` (đổi)

Với `kind` thuộc năm điểm, `approve` cần thêm `base`:

- `409 changed`: `base` khác dấu hiện tại. Trang phải tải lại.
- `422 checks_not_passed`: phép kiểm của điểm chưa đạt. `message` ghi lý do, ví dụ `"2 style warnings open"`.
- Đạt thì ghi lần duyệt vào phim (R1), rồi ghi quyết định như specs/003.

MCP `answer_review` nhận thêm `base` (tuỳ chọn). Thiếu `base` thì máy chủ dùng dấu hiện tại, áp cho nguồn `api`.

## Sự kiện

Không thêm loại sự kiện. Thao tác đổi trạng thái thì ghi nhật ký việc, nên `job.updated` được phát. Duyệt thì phát `review.decided`.
