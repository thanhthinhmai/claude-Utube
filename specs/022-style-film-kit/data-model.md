# Data model: 022

## Bộ dựng (`my-styles/<slug>/kit/`)

| Phần | Tệp | Ghi chú |
|---|---|---|
| Danh mục | `catalog.json` | nguồn tên duy nhất cho bảng cảnh (bên dưới) |
| Số hậu kỳ | `GRADE.md` | mỗi số mặc định kèm số đo đối chiếu (FR-005) |
| Trang danh mục | `catalog.html` | trang phim hợp lệ: mỗi mục một cảnh 1 s, có `SHOTS`, `CARDS` |
| Module | `stage.js`, `figure.js`, `crowd.js`, `sets/*.js`, `camera.js`, `graphics.js`, `film.js` | contracts/kit-api.md |

### `catalog.json`

```json
{
 "version": 1,
 "sets": ["classroom", "lockers", "gym", "street", "bedroom", "cafeteria", "stadium", "void"],
 "poses": ["stand", "sit", "walk", "hold-phone", "hold-book", "hold-bag", "hold-cup", "hold-paper", "point", "cheer", "shrug"],
 "faces": ["dot", "half", "wow", "happy", "blank", "angry", "sad", "sweat"],
 "hair": ["bald", "short", "bun", "curly"], "hats": ["cap", "beanie"],
 "cams": {"ecu": {"scale": "ecu", "angle": "eye"}, "mid-eye": {"scale": "med", "angle": "eye"}, "ots": {"scale": "med", "angle": "ots"}, …},
 "gfx": ["counter", "menu", "diagram", "bubble", "stat", "title", "chapter", "end-choice"],
 "moods": ["dusk", "alarm", "night", "lilac"],
 "hero_default": {"hoodie": "#d9b23a", "strings": "#ffffff", "hair": "bald", "hat": null, "glasses": false},
 "avoid_hero": {"hoodie": "<màu áo của nhân vật kênh tham chiếu, đo từ bằng chứng>", "min_delta_e": 25}
}
```

Luật: mọi tên trong `catalog.json` có cài đặt trong module (test `node --test`); `sets` ≥ 8 (FR-004); `cams` là bảng tên → `{scale, angle}`, mỗi nhãn cỡ và góc của `shots.json` có ít nhất một cách đặt máy; `hoodies`, `hair_colours` là bảng màu người phụ của khung chứng minh.

## Cảnh (một phần tử của `SCENES` trong trang phim)

| Trường | Kiểu | Bắt buộc | Luật |
|---|---|---|---|
| `id` | chuỗi | có | duy nhất, ví dụ `S001`; thành mã cảnh của `SHOTS` |
| `dur` | số (s) | có | 1,1–6 s (luật nhịp specs/020, `qc plan` kiểm) |
| `set` | tên | có | trong `catalog.sets`, hoặc `custom:<tên>` khi trang tự dựng (ghi rõ trong bảng cảnh) |
| `cam` | tên hoặc `{name, …chỉnh}` | có | trong `catalog.cams` |
| `cast` | danh sách `{who, pose, face, turn, tilt, at, hold, look}` | không | `who`: `hero` hoặc `extra:<hạt giống>`; tên trong danh mục |
| `crowd` | `{n, area, seed}` | không | `n` ≤ 5.000 |
| `gfx` | danh sách `{type, text, at, from, to, …}` | không | `type` trong `catalog.gfx`; chữ in hoa; thời gian nằm trong cảnh |
| `mood` | tên | không | trong `catalog.moods`; mặc định `dusk` |
| `grade` | `{exposure, saturation}` | không | chỉnh riêng cảnh này; `exposure` 0,6–1,0, `saturation` 0,85–1,15 (hệ số nhân); ngoài khoảng thì lỗi. Không đổi số mặc định |
| `fade` | `"in"`/`"out"` | không | ≤ 2 lần mỗi phim (mục 6 `STYLE.md`) |

Từ `SCENES`: `DUR` = tổng `dur`; `SHOTS[i] = [t0, t1, set, id]` liền nhau từ 0; `CARDS` gồm chữ của mọi `gfx`.

## Nhân vật chính của kênh (`channels/<kênh>/channel.json` → `hero`)

| Khoá | Kiểu | Luật |
|---|---|---|
| `hoodie` | màu `#rrggbb` | ΔE (Lab) ≥ `avoid_hero.min_delta_e` so với `avoid_hero.hoodie` của phong cách của kênh |
| `strings` | màu `#rrggbb` | |
| `hair` | tên | trong `catalog.hair` |
| `hat` | tên hoặc `null` | trong `catalog.hats` |
| `glasses` | bool | |

Thiếu `hero` (kênh cũ): hợp lệ, dùng `hero_default`. `attach` chép vào bản chụp của phim: `channel.json` → `film.hero`.

## Bản chép trong phim (`films/<tên>/kit/.from`)

```json
{"style": "dusk-hypothetical", "sha256": "<băm các tệp đã chép>", "at": "2026-11-13T10:00:00Z"}
```

Trạng thái: chưa có → `kit use` chép; cùng băm → không làm gì; khác băm → chỉ chép đè khi `--update`.

## Phong cách sau `learn save`

Tệp được chép từ `references/<set>/style/` (danh sách cho phép): `STYLE.md`, `EVIDENCE.md`, `style.json`, `STRUCTURE.md`, `shots.json`, `styleframe/**`, `styleframe.jpg`. Với `--update`, giữ của phong cách cũ: `kit/`, `DEMO.md`, `demo/`, `demo-checks.json`, `test.jpg`, `test.mp4`.

## Phim mẫu (`my-styles/dusk-hypothetical/`)

`DEMO.md` (theo mẫu của thư viện), `demo/` (`index.html` có `SCENES`, `lines.json`, `cues.json`, `mix.py`, `build.sh`, `CREDITS`), `demo-checks.json` (kết quả các tầng, mốc màn, số bối cảnh, fps), `test.jpg`; `test.mp4` ngoài git.
