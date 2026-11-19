# Contract: lệnh mới và lệnh sửa (022)

Mã thoát dùng chung của xưởng: 0 là xong, 2 là sai đầu vào hoặc không làm được (kèm lý do), 1 là lệnh kiểm thấy lỗi. Thông báo tiếng Anh, ngắn.

## `kit use <film> [--style S] [--update] [--json]` (mới)

| Tình huống | Kết quả |
|---|---|
| chưa có `films/<film>/kit/` | chép `my-styles/<S>/kit/` (trừ `test/`), ghi `kit/.from`, in `kit: <S> (<8 ký tự băm>) → films/<film>/kit/`; thoát 0 |
| đã có, cùng băm | in `kit: up to date`; thoát 0 |
| đã có, khác băm, không `--update` | in `kit: films/<film>/kit/ is from <băm cũ>; the style has <băm mới>. Use --update to replace it`; thoát 2 |
| phong cách không có `kit/`, hoặc không tìm ra phong cách | thoát 2 kèm lý do |
| hồ sơ kênh của phim không có `hero` | vẫn chép; in thêm `hint: set the channel hero with "channel set <kênh> hero hoodie=#rrggbb …"` |
| `hero` của phim cùng nhóm màu với `avoid_hero` | thoát 2: `hero: hoodie too close to the reference character (ΔE <n> < 25)` |

`<S>` lấy từ `--style`, rồi `channel.json` của phim (`film.style`). Phong cách được tìm trong `my-styles/` (phong cách thư viện không có kit).

## `channel set <slug> hero <khoá=giá trị…>` (sửa)

- Khoá: `hoodie`, `strings` (`#rrggbb`), `hair` (`bald|short|bun|curly`), `hat` (`cap|beanie|none`), `glasses` (`yes|no`). Chỉ đổi khoá được nêu.
- Sai khoá hoặc giá trị: thoát 2. Áo cùng nhóm màu với `avoid_hero` của phong cách của kênh (ΔE < 25): thoát 2.
- `channel show` in thêm dòng `Hero: hoodie #d9b23a · strings #ffffff · hair bald`.
- `channel attach` chép `hero` vào `film.hero` của bản chụp.

## `learn save` (sửa)

Chỉ chép các tệp trong danh sách cho phép (data-model.md, "Phong cách sau learn save"). Mỗi tệp bị bỏ in một dòng `skipped: <đường dẫn>`. Không đổi tham số, không đổi mã thoát.

## `check-names` (không đổi lệnh)

Được gọi thêm trên `STRUCTURE.md`, mọi tệp `kit/*.js`, `kit/catalog.json`, `demo/*` (SC-007).
