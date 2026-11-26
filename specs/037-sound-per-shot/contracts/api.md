# Contract: API của app và proxy

## App (trang việc, phim AE)

| Đường | Thay đổi |
|---|---|
| `GET /jobs/{id}/steps` | (sửa) khối mới `sound` (`null` với phim trang): `{mix:{url:"out/mix.wav", built_at}\|null, video:"out/render.mp4"\|null, scope:"all"\|"cc0", library:{ready, entries}, notes, notes_base, plan_base, shots:[{id, t0, t1, on, cues:[{id, action, anchor, query, entry, at, len_s, gain_db, cut, fade_s, by, state, why, sound:{id,name,credit,source,duration}, alts[≤7]}], silences, notes_open}], missing, dropped, length, timing_source, error}`. Trước 035: khung phát `video` (bản dựng có tiếng) từ `t0` đến `t1`, không có thì `mix`. Sau 035: thêm `clip_url` (clip nháp câm). |
| `GET /jobs/{id}/files/out/mix.wav`, `…/files/out/render.mp4` | (sửa danh sách cho phép) hỗ trợ `Range`. |
| `GET /api/v1/sound/search?q=` | "Add a sound": tìm trong kho (12 kết quả, chữ, không đường dẫn) theo phạm vi người xem (chủ xưởng → all, khách → cc0); kho ít kết quả tốt và có khoá → lấy thêm Freesound CC0 trước. `422` khi `q` trống. |
| `GET /api/v1/sound/preview/{entry}` | Phát một mục kho (≤ 30 s). 403 khi mục là Sonniss và người xem không phải chủ xưởng (FR-013a). |
| `POST /jobs/{id}/actions` | (sửa) `point: "mix"`, `op`: `cue-set {cue, entry?, offset_f?, gain_db?, cut?, fade_s?, len_s?}`, `cue-rm {cue}`, `cue-add {shot, action, query, motion?\|line?+word?\|at? (giây trong shot)}`, `shot-set {shot, on: yes\|no}`, `sound-note-add {shot, text}`, `sound-note-delete {shot, note}`. `base` = `plan_base` (op cue, shot) hoặc `notes_base` (op ghi chú); lệch → trạng thái `conflict`. Sau mỗi op cue app chạy `sound mix` (≤ 30 s, SC-006); op ghi chú không làm bước nào cũ. |
| `POST /reviews/{rid}/decision` | (sẵn có) kind `mix`: `approve` (nút tắt khi còn ghi chú mở); `revise` không kèm chữ = "Send N notes to Claude": ghi chú lấy "N sound notes on: S2, S5", ghi chú đang mở thành lượt (`lot`); duyệt `mix` mới hoặc việc hỏng thì lượt đóng. |
| `GET /films/{film}/sound` | Khối `sound` của phim AE đã xong (như trên; `video` phát qua `/films/{film}/video`). 422 `not_ae` với phim trang. |
| `POST /films/{film}/sound/notes {shot, text, base?}` · `DELETE /films/{film}/sound/notes/{shot}/{note}?base=` | Ghi chú Sound trên trang phim (base 16 ký tự hex; lệch → 409 `changed`; shot lạ → 422 `bad_shot`). |
| `POST /films/{film}/sound/fix` | Chỉ trong app (chế độ trên máy → 409 `app_only`): ghi chú mở thành lượt, tạo việc `fix` `target: "sound"` `{film, notes}`. 422 `no_notes`; 409 `busy` khi lượt trước còn chạy. Xong: `sound/plan.json`, `sound/cache`, `out/mix.wav`, `out/audio.m4a`, `CREDITS`, `out/render.mp4`, `<phim>.mp4` về phim của khách, trả lời ghi vào ghi chú; hỏng: phim giữ nguyên, ghi chú vẫn mở (`failed_lot`). |
| `GET/POST/DELETE /api/v1/admin/sound`, `POST /api/v1/admin/sound/index`, `PUT/DELETE /api/v1/admin/sound/freesound-key` | Thư mục kho (thêm/xoá, lập lại mục lục chạy nền), khoá Freesound (lưu sau một lần gọi thử; trả 4 ký tự cuối). Chỉ chủ xưởng. |

## Proxy (chỉ việc của agent)

| Đường | Hành vi |
|---|---|
| `POST /internal/sound/search {query, cat?, dur?}` | Tìm trong mục lục theo phạm vi của chủ việc (`admin` → all, `customer` → cc0); nếu không đủ điểm và có khoá → tìm Freesound CC0, tải, thêm mục. Trả 8 kết quả (chữ, không âm thanh). Log: số kết quả, không khoá. |
| `POST /internal/sound/fetch {entry, film}` | Kiểm phạm vi, chép tệp vào `films/<phim>/sound/cache/` của việc. 403 `scope` khi khách xin mục Sonniss. |

Dòng lệnh không có app: `soundlib` đọc trực tiếp `$STUDIO_DATA/sound/`, phạm vi `all`, khoá Freesound từ `FREESOUND_API_KEY`.
