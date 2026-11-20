# Data Model: Bộ dựng SVG cho Sketch Explainer

## Cảnh (scene) — một dòng của `SCENES` trong trang phim

| Trường | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `id` | chuỗi `S001…` | có | mã cảnh, dùng trong mọi báo lỗi |
| `dur` | số giây | có | khớp mốc lời (do `build_plan` của phim tính) |
| `set` | tên trong `catalog.sets` hoặc `custom:<tên>` | có | |
| `custom` | danh sách phần `[tên phần, {tham số}]` | khi `set` là `custom:` | |
| `cam` | `{size, move, from, to, drift, hold, ots}` | không | `size`: ecu cu med wide huge insert; `move`: push pull still follow (mặc định theo luật xen kẽ của `camera.js`); `hold` mặc định 0,3 |
| `cast` | danh sách người trong cảnh | không | bảng dưới |
| `board` | `{k: num bars list vs pie line, x, y, w, h, look: wb chalk tv paper, at, …}` | không | số chỉ từ `SOURCES.md` (luật xưởng) |
| `sign` | `{who, text, sub, col}` | không | biển cầm tay của một người trong `cast` |
| `bub` | danh sách `[who, chữ, t]` | không | người thật: chỉ ký hiệu hoặc trích dẫn có nguồn (FR-018) |
| `think` | `{who, picture}` | không | bong bóng suy nghĩ có hình nhỏ |
| `props` | danh sách `[tên đạo cụ, x, y, cỡ, tham số]` | không | tên trong `catalog.props` |
| `acts` | danh sách `[t, kind, who, {tham số}]` | không | hành động ghi tay; lịch tự động lấp chỗ trống |
| `cap`, `lab` | chú thích và nhãn mũi tên | không | như `scenes2.js` cũ |
| `trans` | `cut` (mặc định) hoặc `dissolve` | không | `dissolve` chỉ khi nhảy thời gian hoặc nơi chốn |
| `card` | `{big, small}` | không | thẻ chương (nền gần đen, chữ trắng viết tay) |

## Người trong cảnh (cast member)

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `who` | tên vai chung (`catalog.roles`), `narrator`, `extra:<n>` (mặt trắng), hoặc `person:<slug>` | `person:` phải có trong `films/<tên>/people/index.json` |
| `x`, `s` | vị trí ngang, cỡ (0,3–1,2) | `y` tự tính từ đường sàn của bối cảnh |
| `pose`, `expr`, `face`, `look`, `view` | tên trong `catalog.poses`, `catalog.exprs`; `view: back` | |
| `walk` | `[x0, x1, t0, t1]` | đi có nhún |
| `still` | đúng/sai | tắt cử chỉ tự động (người cầm biển, người ngồi) |
| `seat` | đúng/sai | ngồi sau bàn của bối cảnh có chỗ ngồi |

## Hành động (event) — đầu ra của `acting.schedule`

| Trường | Ghi chú |
|---|---|
| `t` | giây tính từ đầu cảnh; hành động đầu ở 0,15 |
| `kind` | `gesture`, `expr`, `blink`, `build` (đồ hoạ dựng lên), `pop` (ký hiệu), `enter`, `type` (chữ hiện dần) |
| `who` | chỉ số người trong `cast` hoặc `board` |
| `dur` | mặc định 1,25 giây, sau đó giữ |

Luật: khoảng cách giữa hai hành động 2–3 giây (giả ngẫu nhiên theo `id` cảnh, tất định); cảnh ≥ 4 giây có ít nhất 1 hành động sau giây đầu, cảnh ≥ 6 giây có ít nhất 2 (SC-004).

## Danh mục (`kit/catalog.json`)

`version`, `sets`, `parts`, `roles`, `poses`, `exprs`, `props`, `boards`, `cams`, `trans`, `defaults` (số mặc định kèm dẫn tới `EVIDENCE.md`: nét, máy, lịch hành động, bão hoà bối cảnh), `hero_default`, `avoid_hero` (rỗng).

## Người thật (`people/<slug>/person.json`)

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `slug` | chữ thường, số, gạch nối | tên thư mục |
| `name` | chuỗi | tên thật (chỉ nằm ở thư viện người thật) |
| `role` | chuỗi ngắn | vd. "chief executive of a chip maker" |
| `ref` | `{url, source, license, author}` hoặc `null` | ảnh tham chiếu chỉ để so, không vào git |
| `figure_hash` | sha256 của `figure.js` | tính lúc lưu |
| `approved` | `{hash, at, by, note}` hoặc `null` | `by`: `chat` hoặc `ui`; hợp lệ khi `approved.hash == figure_hash` |
| `history` | danh sách lần duyệt cũ | không xoá |

`figure.js` xuất một đối tượng vai: `{head, hair, hairBack, hairRear, extraFace, brows, browW, skin, skinShade, suit, suitShade, torso}`, cùng định dạng vai chung.

Trạng thái: `chưa duyệt` → (`people approve`) → `đã duyệt`; sửa `figure.js` → băm đổi → `chưa duyệt`.

## Người trong phim (`films/<tên>/people/index.json`)

`{"people": [{"slug", "hash", "copied_at"}]}` cùng bản chép `films/<tên>/people/<slug>/figure.js`. Tầng 1 chặn khi `hash` của bản chép khác `approved.hash` trong thư viện.

## Biến trang thêm cho tầng 1

| Biến | Giá trị |
|---|---|
| `window.KIT_ERRORS` | `[{shot, kind: unknown_set|unknown_pose|unknown_role|unknown_prop|unknown_person|bad_value, name, hint}]` |
| `window.PEOPLE` | `[{slug, hash}]` người thật trang đã nạp |
| `window.BUBBLES` | `[[t0, t1, shot, who, text, person]]` |
