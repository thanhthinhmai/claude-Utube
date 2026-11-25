# Data Model: Duyệt nhân vật cho phim After Effects

Định dạng tệp đầy đủ ở [contracts/files.md](contracts/files.md). Ở đây là thực thể, quan hệ và luật.

## Character (trong phim: `cast/cast.json → characters[]`)

| Trường | Kiểu | Luật |
|---|---|---|
| `id` | chuỗi `[a-z0-9-]{1,32}` | duy nhất trong phim |
| `name` | chuỗi ≤ 40 | hiện trên trang |
| `role` | `hero` \| `support` \| `background` | |
| `kind` | `one` \| `group` | `group` có `members` (2–8 spec) và chỉ có hình nhóm |
| `rig` | `"ball@N"` | N có trong `rigs.lock` |
| `spec` | đối tượng | tham số rig (R3); kiểm khoá theo `contracts/files.md` |
| `needs` | `{expressions[], poses[], walk}` | mỗi mục `{key, label, para}`; `para` là mã đoạn kịch bản (`P01`…) |
| `from_library` | `{channel, id, v}` \| null | có khi lấy từ kho |
| `approved` | `{fingerprint, at, by, source}` \| null | `fingerprint` = băm `spec`+`rig`+`needs` + băm `sheet.json` của nhân vật |

**Trạng thái nhân vật**: `new` (chưa có bảng mẫu) → `ready` (có bảng mẫu, chưa duyệt) → `approved`; `approved` → `changed` khi dấu hiện tại khác dấu lúc duyệt hoặc khi có ghi chú mở; `changed` → `ready` sau khi vẽ lại; nhân vật từ kho đủ hình → `approved` ngay.

## Cast (cấp phim: `cast/cast.json`)

- `version: 1`, `characters[]`, `save_to_library: bool` (mặc định true), `channel` (lấy từ kênh của phim).
- **Điểm `cast`** (points.py): `approved` ⇔ mọi nhân vật `approved` và dấu điểm khớp; `skipped` khi phim không phải AE hoặc `characters` rỗng (lý do "no characters").

## Cast sheet (`cast/sheets/<id>/`)

- `sheet.json`: `{character, rig, built_at, frames:[{key, group: turn|expr|pose|walk|group, label, para?, file|null, missing_reason?}]}`.
- Ảnh `<key>.jpg`, clip `walk.mp4`. Bản trước ở `cast/sheets/<id>.prev/` (đúng một bản, FR-014).

## Cast note (`cast-notes.json`)

| Trường | Kiểu | Luật |
|---|---|---|
| `id` | `n-<8hex>` | |
| `kind` | `note` \| `view` | `view` = yêu cầu vẽ một hình thiếu; `frame` bắt buộc; mỗi `frame` tối đa một `view` mở |
| `frame` | mã hình \| null | null = ghi chú chung |
| `x`, `y` | số 0–100 \| null | chỉ khi `frame` là ảnh; một chữ số thập phân |
| `text` | chuỗi 1–2000 | |
| `done` | bool | |
| `reply` | chuỗi ≤ 2000 | câu trả lời của Claude |
| `by`, `created`, `updated` | | |

- Cấp tệp: `{version:1, characters:{<id>:{notes:[…]}}, lot?:{job, notes:[ids], since}}`; `base` = sha256 nội dung tệp.
- Thêm ghi chú mở lên nhân vật `approved` → nhân vật `changed` (FR-012).
- Ghi chú thêm khi có `lot` đang chạy không vào lô đó (FR-013).

## Library character (kho của kênh)

- Đường dẫn: `<owner>/channels/<kênh>/cast/<id>/v<n>/character.json` + `sheet/`.
- `character.json`: `{id, name, role, kind, rig, spec, frames_approved:[keys], approved:{at, by, film}, films:[names]}`.
- `index.json`: `{characters:{<id>:{name, latest, versions:[{v, rig, approved_at}]}}}`.
- Bản đã ghi không bao giờ sửa (FR-017); chỉ `films` được nối thêm.
- **Báo bản rig mới**: nhân vật có `rig = ball@N` và `rigs.lock` có `ball@M`, M > N → "New rig version".
- **Xem trước**: `v<n>.preview/` (một bản), xoá khi cập nhật hoặc bỏ.

## Rig version (`tools/ae/rigs.lock`)

- `{"ball@1": "<sha256>", …}`; thư mục `tools/ae/kit/rigs/ball/v1/` bất biến sau khi khoá.
- Danh mục của rig (`catalog()` trong jsx): `{views:[front,back,34], expressions:[…], poses:[…], walk:true}`.
