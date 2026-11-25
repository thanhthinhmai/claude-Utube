# Contract: tệp của tính năng cast

Mọi JSON là UTF-8, ghi nguyên tử (ghi tệp tạm rồi đổi tên). Màu là `#rrggbb`.

## `films/<phim>/cast/cast.json`

```json
{
  "version": 1,
  "channel": "default",
  "save_to_library": true,
  "characters": [
    {
      "id": "hero",
      "name": "You (hero)",
      "role": "hero",
      "kind": "one",
      "rig": "ball@1",
      "spec": {
        "hoodie": "#e8604c", "pants": "#262a3d", "shoes": "#f4f2ee",
        "hat": {"kind": "beanie", "color": "#4f7a4a"},
        "headColor": "#141418", "stripe": null, "tie": null, "hood": true, "brows": false
      },
      "needs": {
        "expressions": [{"key": "wide", "label": "Wide-eyed", "para": "P01"}, {"key": "yawn", "label": "Sleepy", "para": "P04"}],
        "poses": [{"key": "situp", "label": "Sit up in bed", "para": "P01"}, {"key": "guitar", "label": "Guitar", "para": "P02"}],
        "walk": true
      },
      "from_library": null,
      "approved": null
    },
    {
      "id": "classmates", "name": "Classmates ×4", "role": "background", "kind": "group", "rig": "ball@1",
      "members": [{"hoodie": "#4f7fc8", "hat": {"kind": "cap", "color": "#d9a640"}}, {"hoodie": "#5aa064"}],
      "needs": {"expressions": [], "poses": [], "walk": false},
      "from_library": null, "approved": null
    }
  ]
}
```

- `spec` khoá cho phép (rig ball@1): `hoodie`, `pants`, `shoes`, `headColor`, `rimColor`, `hat` (`{kind: beanie|cap|curly|puffs|bun|none, color}`), `stripe` (màu|null), `tie` (màu|null), `hood` (bool), `brows` (bool), `pupils` (số 0.7–1.3), `scale` (số 0.6–1.4). Khoá lạ → lỗi `bad_spec`.
- `approved`: `{"fingerprint": "<sha256[:16]>", "at": "ISO", "by": "<người>", "source": "ui|chat|library"}`.
- `from_library`: `{"channel": "default", "id": "hero", "v": 2}`.

## `films/<phim>/cast/catalog.json` (do `ae sheet` ghi từ rig)

`{"rig": "ball@1", "views": ["front","back","34"], "expressions": ["smile","grin","flat","frown","open","o","wide","yawn",…], "poses": ["down","hips","wave",…], "walk": true}`

## `films/<phim>/cast/sheets/<id>/sheet.json`

```json
{"character": "hero", "rig": "ball@1", "built_at": "ISO", "fingerprint": "<sha256[:16]>",
 "frames": [
   {"key": "front", "group": "turn", "label": "Front", "file": "front.jpg"},
   {"key": "34", "group": "turn", "label": "3/4 view", "file": null, "missing_reason": "build error: …"},
   {"key": "expr-wide", "group": "expr", "label": "Wide-eyed", "para": "P01", "file": "expr-wide.jpg"},
   {"key": "walk", "group": "walk", "label": "Walk loop", "file": "walk.mp4"}
 ]}
```

Ảnh JPEG cạnh dài 720 px, ≤ 300 KB; `walk.mp4` H.264 ≤ 400 px, 2,5 s, không tiếng. Bản trước: `cast/sheets/<id>.prev/` (cùng cấu trúc).

## `films/<phim>/cast-notes.json`

```json
{"version": 1,
 "characters": {
   "friend": {"notes": [
     {"id": "n-1a2b3c4d", "kind": "note", "frame": "front", "x": 42.5, "y": 8.0,
      "text": "Hair: bigger curls over the forehead", "done": false, "by": "owner",
      "created": "ISO", "updated": "ISO", "reply": null},
     {"id": "n-5e6f7a8b", "kind": "view", "frame": "34", "x": null, "y": null, "text": "Draw this view", "done": false, "by": "owner", "created": "ISO", "updated": "ISO"}
   ]}
 },
 "lot": {"job": "j-…", "notes": ["n-1a2b3c4d"], "since": "ISO"}}
```

- Lưu có `base` = sha256 của nội dung hiện tại; lệch → 409 `changed` kèm `current`.
- `x`, `y` chỉ khi `frame` trỏ tới hình có `file`; ngoài 0–100 → lỗi `bad_pin`.

## Kho nhân vật: `$STUDIO_DATA/accounts/<owner>/channels/<kênh>/cast/`

```text
cast/index.json
cast/<id>/v1/character.json
cast/<id>/v1/sheet/{sheet.json, *.jpg, walk.mp4}
cast/<id>/v2.preview/…            # xem trước rig mới (tối đa một)
```

`character.json`: `{"id","name","role","kind","rig","spec"|"members","frames_approved":["front","back","34","expr-wide",…],"approved":{"at","by","film"},"films":["ae-sleepless-test"]}`.

`index.json`: `{"characters": {"hero": {"name": "You (hero)", "latest": 1, "versions": [{"v": 1, "rig": "ball@1", "approved_at": "ISO"}]}}}`.

## `tools/ae/rigs.lock`

`{"ball@1": "<sha256 của mọi tệp trong tools/ae/kit/rigs/ball/v1/, sắp theo tên>"}`
