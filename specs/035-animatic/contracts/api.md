# Contract: API của app

## Trang việc (phim đang làm)

| Đường | Thay đổi |
|---|---|
| `GET /jobs/{id}/steps` | (sửa) phim AE: `steps[]` có `Animatic` sau `Voice`, không có `Look/Picture/Shots`; `points` có `animatic`; khối mới `animatic`: `{draft:{url, current, built_at, seconds}\|null, duration, silence, limit, shots:[{id,t0,t1,frame_url,clip_url,lines:[{id,at,end,text}],fit:{delta_s,end_new,very_short,motions[],state}\|null,notes_open}], notes:<animatic/notes.json>, notes_base, timing_base, can_undo, building:{shots[]}\|null}`. |
| `GET /jobs/{id}/files/animatic/<file>` | (sửa danh sách cho phép của specs/025) `draft.mp4`, `draft.prev.mp4`, `clips/*.mp4`, `frames/*.jpg`. Hỗ trợ `Range` để phát video. |
| `POST /jobs/{id}/actions` | (sửa) `point: "animatic"`, các `op`: `fit_accept {shots:[…]\|"all"}`, `fit_skip {shot}`, `fit_undo {}`, `note_add {shot, at?, x?, y?, text}`, `note_delete {shot, note}`, `draft_rebuild {}`. Có `base` (`timing_base` cho fit, `notes_base` cho ghi chú); lệch → 409 `changed` kèm bản hiện tại. Sau `fit_*` app tự xếp `ae draft --shots <các shot đổi>` (FR-016). |
| `POST /reviews/{rid}/decision` | (sẵn có) kind `animatic`: `approve` (nếu silence > 20% cần `anyway: true` từ giao diện, nếu không 422 `needs_anyway`); `revise` = "Send notes to Claude", `note` tự điền "N notes on: S2, S6". |

## Phim đã xong (ngoài việc làm phim)

| Đường | Thay đổi |
|---|---|
| `POST /films/{film}/animatic/fix {notes:[…]}` | Tạo việc `fix` `input.target="animatic"`, `input.shots=[…]`. 409 `ae_unavailable` khi cầu nối chưa sẵn sàng (như specs/032). |

## Việc `fix` với `target: "animatic"`

Agent nhận các ghi chú của lô, sửa mã các shot đó, chạy `ae draft <phim> --shots …`, trả lời từng ghi chú (`animatic notes reply`), không duyệt. Kết thúc: bước Animatic về `waiting`.
