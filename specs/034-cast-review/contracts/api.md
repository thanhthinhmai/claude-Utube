# Contract: API của app

Tiền tố `/api/v1`. Quyền như các route ghi chú của specs/029 (đọc: người xem; ghi: chủ xưởng hoặc người có quyền ghi). Lỗi theo dạng `{"error": {"code", "message", …}}` sẵn có.

## Trang việc (phim đang làm)

| Route | Làm gì |
|---|---|
| `GET /jobs/{id}/steps` | (sửa) thêm `steps[]` có `Cast`; `points` có `cast`; khối mới `cast`: `{characters:[{id,name,role,kind,state,source,rig,spec\|members,needs,sheet:{frames[]}\|null,notes_open}], notes:<cast-notes.json>, notes_base, save_to_library, library_available}`. |
| `GET /jobs/{id}/files/cast/sheets/<id>/<file>` | (sửa danh sách cho phép của specs/025) ảnh và clip bảng mẫu, cả `<id>.prev/`. |
| `POST /jobs/{id}/actions` | (sửa) `point: "cast"`, các `op`: `cast_note_add {character, kind, frame?, x?, y?, text}`, `cast_note_delete {character, note}`, `cast_view_toggle {character, frame}`, `cast_approve {character}`, `cast_save {on}`. Có `base` (của `cast-notes.json` hoặc dấu cast). |
| `POST /reviews/{rid}/decision` | (sẵn có) yêu cầu duyệt kind `cast`: `approve` = "Approve cast" (duyệt mọi nhân vật); `revise` = "Send notes to Claude", `note` tự điền "N notes on: friend, hero". Claude của việc nhận và vẽ lại. |
| `POST /jobs/{id}/cast/resend` | (Phase 9, T063) Việc phim (của app) thất bại hoặc bị dừng giữa lượt vẽ lại (`cast-notes.json` → `failed_lot.job` = việc này) còn ghi chú mở: mở lại chính việc đó ở bước Cast (không tốn credit thêm), tạo yêu cầu duyệt `cast` đã gửi lại ghi chú; worker tiếp tục phiên Claude. 409 `not_allowed`/`too_many_queued`, 422 `no_notes`. Thư mục việc được giữ trong `review_timeout_days` để gửi lại được. |

## Phim đã xong và kho nhân vật (ngoài việc làm phim)

| Route | Làm gì |
|---|---|
| `GET /cast-library` | `{available, channels:[{channel, characters:[{id,name,role,latest,rig,approved_at,films,new_rig}]}]}`. `available: false` khi không có kho (không ở chế độ app). |
| `GET /cast-library/{channel}/{id}` | Bản mới nhất + danh sách bản + `preview` (nếu có), kèm `sheet.frames`. |
| `GET /cast-library/{channel}/{id}/v{n}/{file}` | Ảnh, clip; `v{n}.preview` cũng được. |
| `POST /cast-library/{channel}/{id}/preview {rig}` | Tạo việc `fix` (`input.target="cast"`, `input.mode="preview"`, `input.rig`). 409 `ae_unavailable` khi cầu nối chưa sẵn sàng (như specs/032). |
| `POST /cast-library/{channel}/{id}/update` | Biến bản xem trước thành bản mới chưa duyệt. 422 `no_preview`. |
| `POST /cast-library/{channel}/{id}/approve` | Duyệt bản mới nhất. |
| `POST /cast-library/{channel}/{id}/fix {notes:[…]}` | Ghi chú lên nhân vật trong kho → việc `fix` (`target="cast"`, `mode="library"`); kết quả là bản mới chưa duyệt. |

## Việc `fix` với `target: "cast"`

- `jobs.build("fix", …)` với `input = {kind:"fix", target:"cast", mode:"preview"|"library", channel, character, rig?, notes?}`.
- Worker dựng một thư mục làm việc tạm `work/cast/<channel>-<id>/` gồm `cast/cast.json` một nhân vật (từ kho), `cast-notes.json` (nếu có), rồi agent chạy `ae sheet`, trả lời ghi chú; `finish_fix` chép `cast/sheets/<id>/` vào `v<n+1>.preview/` (preview) hoặc `v<n+1>/` chưa duyệt (library).
