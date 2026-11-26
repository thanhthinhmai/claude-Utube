# Data Model: Âm thanh theo shot (037)

## Kho tiếng — `$STUDIO_DATA/sound/` (ngoài repo, thuộc máy)

### `roots.json`
`{version: 1, roots: [{path, kind: "sonniss", added_at}]}`. Thư mục dưới `references/` hay dữ liệu học bị từ chối (R11).

### `library.db` (SQLite)
Bảng `entry`:

| Trường | Kiểu | Luật |
|---|---|---|
| `id` | text | `s:` + sha1(path)[:12] (Sonniss/người dùng) hoặc `fs:<freesound id>` |
| `path` | text | đường dẫn tuyệt đối trên máy |
| `size`, `mtime_ns` | int | khoá lập lại (FR-011) |
| `name` | text | tên tệp không đuôi, `_` → khoảng trắng |
| `category`, `subcategory` | text | từ UCS `CatID` hoặc thư mục |
| `description`, `keywords` | text | `bext`, `INFO`, `iXML`, tag Freesound |
| `duration`, `rate`, `channels` | số | header |
| `source` | `sonniss\|freesound\|user` | |
| `credit` | text | "Sonniss GDC 2024 · <tên gói>" hoặc "Freesound #123 by user" |
| `url` | text | trang nguồn (Freesound) hoặc rỗng |
| `license` | `sonniss-gdc-2.0\|cc0-1.0` | lúc lấy về; không đổi sau đó |
| `fetched_at` | text | Freesound |
| `ok` | bool | false = tệp hỏng (liệt kê riêng, FR-010) |

Bảng ảo `entry_fts` (FTS5) trên `name, category, subcategory, description, keywords`.

### `freesound/<id>.ogg`
Bản xem trước HQ của tiếng CC0 (R4).

## Phim — `films/<phim>/sound/`

### `plan.json` — danh sách tiếng (Sound plan)

| Trường | Kiểu | Luật |
|---|---|---|
| `version` | 1 | |
| `timing_sha` | text | băm `timing.json → frames` lúc resolve |
| `profile` | `style\|default` | phần tiếng của phong cách hay luật mặc định (Edge case) |
| `cues` | `[cue]` | |
| `off` | `[shot]` | shot tắt tiếng động (FR-005a); theo thứ tự shot, shot không còn thì bỏ |

`cue`:

| Trường | Kiểu | Luật |
|---|---|---|
| `id` | text | `c01`…, bền qua các lần chạy lại |
| `shot` | id | có trong `timing.json → frames` |
| `action` | text | tên hành động, vd. "eyes pop open" |
| `anchor` | object | một trong `{motion, edge, offset_f}` · `{line, word?, offset_f}` · `{shot_at}` · `{span: "shot"}` (R6) |
| `query`, `cat` | text | từ khoá tìm và loại UCS gợi ý |
| `entry` | id \| null | mục kho đã chọn; null = missing |
| `alts` | `[id]` | ≤ 7 tiếng thay thế cùng loại |
| `len_s` | số \| null | null = hết tệp (hoặc hết shot với `span`) |
| `gain_db` | số | so với mức giọng, trong khoảng `sfx_db` của phong cách |
| `cut` | `hard\|fade\|over` | + `fade_s` khi `fade` |
| `by` | `auto\|user\|claude` | `user` = sửa của người dùng, giữ qua các lần chạy lại (FR-025) |
| `state` | `placed\|dropped\|missing\|off` | + `why`; `off` = shot đang tắt tiếng, cue vẫn được tính mốc nhưng không trộn |
| `at` | số | mốc tuyệt đối (giây) sau resolve; chỉ để đọc |

`silences`: `[{shot, anchor, len_s, db}]` — khoảnh khắc lặng có chủ ý (FR-006).

Chuyển trạng thái: `resolve` (khi `timing_sha` khác hoặc sau mỗi sửa) → tính `at`; neo không còn → `dropped` + `why` ("motion 'Hand R · Rotation' is gone after the cut"); `entry` null → `missing` + `why` (từ khoá đã tìm). Cue `by: user` không bao giờ bị lập lại xoá; nếu dropped thì báo trên trang (Story 3 kịch bản 4).

### `cache/<entry>.<ext>`
Bản sao tiếng đã chọn (R5), ngoài git.

### `stems/fx.wav`, `stems/voice.wav`
Lớp của lần trộn gần nhất (tính khác biệt, phát thử).

### `notes.json`
Mẫu `pins.py` (035): `{version, base_sha, shots: {S2: [{id, text, state, reply, lot}]}}` (ghi chú chung, không ghim x/y).

### `CREDITS` của phim
Khối được thay mỗi lần trộn, giữa `# sound effects (studio, 037)` và `# end sound effects`: một dòng mỗi mục kho đã dùng: `<credit> · <tên tiếng> — <license>[ — <url>]` (FR-016).

## Phong cách — học tiếng

### `references/<set>/profile/<v>/sfx.json`

| Trường | Kiểu |
|---|---|
| `video`, `models` | id; `{separator, ast, clap}` có phiên bản |
| `events` | `[{t, len, layer: "fx"\|"vocal_off_words", ast: [[label, p]×5], clap: [label, p], agree: bool, trust: "sure"|"likely"|null, label, word?: {text, t}, shot?, db_vs_voice, cut?: {kind, fade_s}}]` |
| `silences` | `[{t, len, db, word}]` |
| `ontology` | `{label: ancestor_level2}` cho các nhãn đã gặp (bảng đồng ý, FR-018) |

### `my-styles/<style>/template.json → sound.sfx` (phim đọc qua `kit/template.json` của phim hoặc `film.json → style`)

`{per_min, gain_db: [p25, p50, p75], actions: [{action, label, n, trust: "sure", n_sure, evidence: [[v, t]]}], hints: [{… trust: "likely"}] (≤ 10, hướng A: chỉ là gợi ý), silences: {db, len_s, evidence}, cut: {kind, fade_s, evidence}, unsure_n}` — chỉ số đo, nhãn và mốc (FR-022).

## Điểm duyệt `mix` (phim AE) — `checks.json → reviews`

Như specs/026; vân tay thêm `sound/plan.json` + ghi chú mở (R10). Trạng thái: `not_reached` (animatic chưa duyệt) → `waiting` → `approved` → `stale`.
