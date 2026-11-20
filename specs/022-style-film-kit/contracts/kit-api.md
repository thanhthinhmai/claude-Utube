# Contract: bộ dựng trong trang phim

Trang phim nằm ở `films/<tên>/index.html`, bộ dựng ở `films/<tên>/kit/` (chép bằng `kit use`). Trang dùng importmap như khung chứng minh:

```html
<link rel="stylesheet" href="/core/fonts/fonts.css">
<script type="importmap">{"imports":{"three":"/node_modules/three/build/three.module.js","three/addons/":"/node_modules/three/examples/jsm/"}}</script>
<script type="module">
import { film } from './kit/film.js';
const SCENES = [
  { id: 'S001', dur: 1.8, set: 'cafeteria', cam: 'ecu', cast: [{ who: 'hero', pose: 'sit', face: 'half' }] },
  { id: 'S002', dur: 2.4, set: 'cafeteria', cam: 'wide-high', crowd: { n: 80, seed: 3 },
    cast: [{ who: 'hero', pose: 'hold-phone', face: 'dot' }, { who: 'extra:7', pose: 'point', face: 'wow', turn: 30 }],
    gfx: [{ type: 'counter', text: '$20', from: 0, to: 20, at: 0.3 }] },
  // …
];
await film({ scenes: SCENES, cues: './cues.json' });
</script>
```

specs/026: `scenes` may be left out; `film()` then reads `./scenes.json` (`{custom: [names], scenes: [...]}`), which the job page edits. Each name in `custom` needs a builder in `film({custom})`.

## `film(opts)` → Promise

| Tuỳ chọn | Kiểu | Mặc định | Việc |
|---|---|---|---|
| `scenes` | danh sách cảnh | bắt buộc | data-model.md, "Cảnh" |
| `cues` | đường dẫn hoặc danh sách `[t0, t1, chữ]` | `./cues.json` nếu có | phụ đề |
| `hero` | đối tượng | `film.hero` của `./channel.json`, rồi `hero_default` | nhân vật chính |
| `custom` | `{tên: (ctx) => Group}` | `{}` | bối cảnh tự dựng cho `set: 'custom:<tên>'` |
| `size` | `[w, h]` | cỡ cửa sổ | |

Sau khi xong, trang có (hợp đồng trang của thư viện và specs/020 `contracts/film-page.md`):

| Biến | Giá trị |
|---|---|
| `window.DUR` | tổng `dur` |
| `window.SHOTS` | `[[t0, t1, set, id]]` liền nhau từ 0 tới `DUR` |
| `window.CARDS` | `[[t0, t1, id, chữ]]`, sinh từ mọi `gfx` có chữ |
| `window.CUES` | phụ đề đã nạp |
| `window.render(t)` | vẽ khung ở thời điểm `t`; tất định, gọi theo thứ tự bất kỳ |
| `window.READY` | `true` khi mọi bối cảnh dùng tới và phông đã nạp |
| `window.CLEAN` | trang đọc mỗi khung: bật thì không vẽ phụ đề và đồ hoạ có chữ |

Lỗi: tên không có trong `catalog.json`, `dur` ngoài 1,1–6 s, `grade` ngoài khoảng hoặc `gfx` ngoài cảnh → `film()` ném lỗi có mã cảnh (`S014: unknown pose "hold-lamp"`), không đặt `READY`.

## Module dùng riêng (khi cần chỉnh sâu một cảnh)

| Module | Xuất | Ghi chú |
|---|---|---|
| `stage.js` | `makeStage(size)` → `{renderer, scene, post, grade(mood), draw()}` | hậu kỳ mặc định theo `GRADE.md` |
| `figure.js` | `makeFigure({hoodie, strings, hair, hat, glasses, seed})` → `{group, pose(name, t), face(name), look(turn, tilt), hold(item)}` | |
| `crowd.js` | `makeCrowd({n, area, seed, camera})` → `{group, update(camera, t)}` | ba mức chi tiết |
| `sets/<tên>.js` | `build(ctx)` → `{group, anchors, lights}` | `anchors`: chỗ đặt hero, người phụ, đám đông, máy |
| `camera.js` | `place(cam, name, anchors, opts)` | lớp trước, vật che tiền cảnh khi `ots` |
| `graphics.js` | `drawGfx(ctx2d, g, localT, area)`; `cardsOf(scene, t0)` | `cardsOf` là phần thuần, có test |

Trang tự dựng (`custom`) dùng các module trên, không viết lại nhân vật, ánh sáng, hậu kỳ hay đồ hoạ (SC-005).
