# Contract: API của app và proxy

## App (trang việc, phim AE)

| Đường | Thay đổi |
|---|---|
| `GET /jobs/{id}/steps` | (sửa) khối mới `sound`: `{mix:{url, built_at}\|null, profile, shots:[{id,t0,t1,clip_url,cues:[cue + {entry_name, credit}], silences[]}], missing:n, dropped:n, notes, notes_base, plan_base, scope:"all"\|"cc0", library:{ready, entries, freesound}}`. `clip_url` = clip nháp của 035 (phát câm, tiếng lấy từ `mix.url` theo `t0`). |
| `GET /jobs/{id}/files/sound/mix.wav` | (sửa danh sách cho phép) hỗ trợ `Range`. |
| `GET /api/sound/preview/{entry}` | Phát một mục kho (≤ 30 s). 403 khi mục là Sonniss và người xem không phải chủ xưởng (FR-013a). |
| `POST /jobs/{id}/actions` | (sửa) `point: "mix"`, `op`: `cue_set {cue, entry?, offset_f?, gain_db?, cut?, len_s?}`, `cue_rm {cue}`, `cue_add {shot, action, query, anchor}`, `note_add {shot, text}`, `note_delete {shot, note}`. Có `base` (`plan_base`/`notes_base`); lệch → 409 `changed`. Sau mỗi op cue app chạy `sound mix` (≤ 30 s, SC-006). |
| `POST /reviews/{rid}/decision` | (sẵn có) kind `mix`: `approve`; `revise` = "Send notes to Claude". |
| `POST /films/{film}/sound/fix {notes}` | Ngoài việc làm phim: tạo việc `fix` `target: "sound"`. |
| `GET/POST/DELETE /api/settings/sound` | Thư mục kho (thêm/xoá, lập lại mục lục chạy nền), khoá Freesound (lưu sau một lần gọi thử; trả 4 ký tự cuối). Chỉ chủ xưởng. |

## Proxy (chỉ việc của agent)

| Đường | Hành vi |
|---|---|
| `POST /internal/sound/search {query, cat?, dur?}` | Tìm trong mục lục theo phạm vi của chủ việc (`admin` → all, `customer` → cc0); nếu không đủ điểm và có khoá → tìm Freesound CC0, tải, thêm mục. Trả 8 kết quả (chữ, không âm thanh). Log: số kết quả, không khoá. |
| `POST /internal/sound/fetch {entry, film}` | Kiểm phạm vi, chép tệp vào `films/<phim>/sound/cache/` của việc. 403 `scope` khi khách xin mục Sonniss. |

Dòng lệnh không có app: `soundlib` đọc trực tiếp `$STUDIO_DATA/sound/`, phạm vi `all`, khoá Freesound từ `FREESOUND_API_KEY`.
