# Contract: bộ dựng Sketch Explainer trong trang phim

Trang phim nằm ở `films/<tên>/index.html`, bộ dựng ở `films/<tên>/kit/` (chép bằng `sh bin/studio kit use <tên>`), người thật ở `films/<tên>/people/` (chép bằng `sh bin/studio people use <tên> <slug…>`).

```html
<script type="module">
import { film } from './kit/film.js';
const SCENES = [
  { id: 'S001', dur: 3.2, set: 'trading-floor', cam: { size: 'med', move: 'push' },
    cast: [{ who: 'narrator', x: 1400, pose: 'raise', expr: 'excited' }, { who: 'trader', x: 600, pose: 'up' }],
    sign: { who: 1, text: '$83', sub: 'a share' } },
  { id: 'S002', dur: 4.1, set: 'whiteboard-room', cam: { size: 'med' },
    cast: [{ who: 'person:jensen-huang', x: 1500, pose: 'pointL' }],
    board: { k: 'bars', title: 'revenue (billions)', items: [['2025', 1.2], ['2026', 16.3, 'green']] },
    bub: [[0, '!', 1.2]] },
  { id: 'S003', dur: 2.8, card: { big: 'The sales', small: 'Chapter 3' } },
];
await film({ scenes: SCENES, cues: './cues.json' });
</script>
```

## `film(opts)` → Promise

| Tuỳ chọn | Kiểu | Mặc định | Việc |
|---|---|---|---|
| `scenes` | danh sách cảnh | bắt buộc | data-model.md, "Cảnh" |
| `cues` | đường dẫn hoặc `[t0, t1, chữ]` | `./cues.json` nếu có | phụ đề do xưởng in |
| `hero` | `{hoodie, hair, hat, glasses}` | `film.hero` của `./channel.json`, rồi `hero_default` | trang phục người dẫn |
| `custom` | `{tên: [[phần, tham số]]}` | `{}` | bối cảnh `custom:<tên>` |

Sau khi xong, trang có (hợp đồng trang của thư viện, specs/020 `contracts/film-page.md`):

| Biến | Giá trị |
|---|---|
| `window.DUR` | tổng `dur` |
| `window.SHOTS` | `[[t0, t1, set, id]]` liền nhau từ 0 tới `DUR` |
| `window.CARDS` | `[[t0, t1, id, chữ]]` từ thẻ chương, bảng, biển |
| `window.TEXTS(t)` | mọi chữ trên khung ở `t`, kèm hộp |
| `window.CUES` | phụ đề đã nạp |
| `window.render(t)` | vẽ khung ở `t`; tất định |
| `window.READY` | `true` khi phông đã nạp; đặt cả khi có lỗi tên |
| `window.CLEAN` | bật thì không vẽ chữ của bảng, biển, bong bóng, thẻ, chú thích |
| `window.KIT_ERRORS` | data-model.md; cảnh lỗi vẽ ô đỏ ghi mã lỗi |
| `window.PEOPLE`, `window.BUBBLES` | data-model.md |

## Tầng 1 (`sh bin/studio qc plan <tên>`)

| Luật | Mức | Khi nào |
|---|---|---|
| `kit_name` | chặn | mỗi mục của `KIT_ERRORS`, kèm tên gần nhất |
| `person_unapproved` | chặn | người trong `PEOPLE` không có trong thư viện, chưa duyệt, hoặc băm bản chép khác băm đã duyệt |
| `person_words` | chặn | bong bóng của người thật có chữ không phải ký hiệu và không khớp trích dẫn trong `SOURCES.md` |

## Module dùng riêng (khi cần chỉnh sâu một cảnh)

| Module | Xuất |
|---|---|
| `core.js` | `el`, `circ`, `rrect`, `bumpy`, `ovalHead`, `segOutline`, `ease`, `clamp01`, `lerp` |
| `rig.js` | `makeChar(parent, cfg)`, `setChar(c, state)`, `POSES`, `EXPRS`, `strokeFor(scale)` |
| `roles.js` | `ROLES`, `extra(n)`, `variant(base, {hair, glasses, hat, suit})`, `narrator(hero)` |
| `acting.js` | `schedule(scene)` → hành động (thuần) |
| `camera.js` | `camFor(scene, prev)` → `{cx, cy, z, cx1, cy1, z1, hold}`; `camAt(cam, lt, d)` (thuần) |
| `sets/index.js` | `SETS`, `PARTS`, `buildSet(name|parts, ctx)` → `{html, fg, floor}` |
| `boards.js` | `boardShape`, `boardText`, `signUI`, `bubbleUI`, `thinkUI`, `cardUI` |

Trang tự dựng chỉ dùng các module trên, không viết lại nhân vật, bối cảnh, máy hay đồ hoạ (SC-001).
