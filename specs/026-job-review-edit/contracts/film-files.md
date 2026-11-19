# Contract: tệp trong thư mục phim

## `checks.json` → `reviews`

Dạng và luật xem [data-model.md](../data-model.md#film-reviews-trong-checksjson--reviews). Chỉ ghi qua `points.py` (bằng `report.update`, có khoá). Tệp này nằm ngoài mọi dấu nội dung.

## `scenes.json` (phim dùng bộ dựng)

```json
{
  "custom": ["platform"],
  "scenes": [
    {"id": "s01", "dur": 3.1, "set": "bedroom", "cam": "wide", "cast": [{"who": "hero", "act": ["stare"]}], "gfx": []}
  ]
}
```

- Mỗi cảnh theo `specs/023-style-craft-template/contracts/kit-api-v2.md`.
- `film()` đọc tệp này khi trang không truyền mảng `scenes`. Trang phim dạng mới:

  ```js
  import { film } from './kit/film.js';
  const platform = ({ THREE, parts }) => { /* … */ };
  await film({ cues: './cues.json', custom: { platform } });
  ```

- `film()` ném lỗi `"custom set \"x\" in scenes.json has no builder"` khi tên trong `custom` không có hàm dựng.
- `scenecheck.mjs <thư mục phim> [tệp scenes]` in `{"ok": true}` hoặc `{"ok": false, "error": "s07: set \"x\" …"}`. Tệp này nằm trong dấu `all`.

## `mix.json`

```json
{"music": "seed:7", "music_under_voice_db": -6.0, "duck_db": -6, "sfx_db": 0}
```

- Dải hợp lệ theo research R11. `kit/sound/mix.py` đọc tệp này khi có.
- Tệp **bị bỏ qua** trong dấu `all` (`tiers.SKIP_NAMES`, `tools/render/lib.mjs`). Nó nằm trong dấu của điểm `mix`.

## `publish/pack.json` (bổ sung specs/011)

- `chosen`: 1, 2 hoặc 3, là chỉ số tiêu đề chính. Thiếu thì coi là 1. `publish` xếp tiêu đề được chọn lên đầu trong `PUBLISH.md`.

## `.check/edits.jsonl`, `.check/busy.json`

Dạng xem data-model. `.check/` nằm ngoài mọi dấu.

## `lines.json` (bổ sung)

- Không đổi dạng. `voice-set` ghi `voice` và `speed` cho mọi dòng. `voice-say` chỉ ghi trường `say`. Chữ `text` không bao giờ bị `edit` sửa.
