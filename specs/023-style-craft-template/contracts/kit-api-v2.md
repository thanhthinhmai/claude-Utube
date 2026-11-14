# Contract: bộ dựng v2 (phần thêm vào specs/022 `contracts/kit-api.md`)

Hợp đồng của 022 giữ nguyên. Bảng cảnh của phim cũ vẫn chạy và cho cùng bố cục; khác duy nhất là nhân vật tự chớp mắt và thở. Các trường dưới đây là phần thêm.

```js
const SCENES = [
  { id: 'S001', dur: 2.2, set: 'cafeteria', cam: 'close', move: 'auto', frame: 'auto', trans: 'cut',
    cast: [{ who: 'hero', pose: 'sit', face: 'half',
             act: [[0.3, 'raise-hand'], [1.4, 'face:wow'], [1.6, 'tilt-head']], talk: [[0.2, 1.1]] }] },
  { id: 'S002', dur: 3.0, set: 'lockers', cam: 'wide-eye', move: { type: 'drift-h', speed: 18 }, trans: 'streak',
    cast: [{ who: 'hero', pose: 'walk', path: [[0, -2, 0], [3, 1.5, 0]] }],
    gfx: [{ type: 'stat', text: '16,000 WORDS', icon: 'speech-stack', at: 0.4 }] },
];
```

## Trường mới

| Trường | Giá trị | Mặc định | Hành vi |
|---|---|---|---|
| `cast[].act` | `[[giây, động tác]]`; động tác trong `catalog.acts` (vd. `raise-hand`, `wave`, `tilt-head`, `nod`, `shrug-up`, `lean-in`, `look:<hướng>`, `face:<biểu cảm>`, `pose:<tư thế>`) | `[]` | động tác lên trong `template.json → motion.rise_s` (dễ dần), rồi giữ tới động tác sau |
| `cast[].talk` | `[[t0, t1]]` | lấy từ khoảng hiện bong bóng của người đó | miệng mấp máy 6–9 lần/s, biên độ ngẫu nhiên theo hạt giống |
| `cast[].path` | `[[giây, x, z]]` | không | đi thật theo đường, chân theo bước; chỉ khi `pose: 'walk'` |
| `cast[].blink` | `false` hoặc `{every: [a, b]}` | theo `template.json` | chớp mắt 0,12 s; thời điểm lấy từ hạt giống của người |
| `move` | `'auto'`, `'still'`, hoặc `{type, speed}` với `type` trong `catalog.moves` (`drift-h`, `drift-v`, `push`, `pull`, `follow`, `tilt`) | `'auto'` | `auto` chọn theo tỉ lệ máy động và tốc độ của cỡ cảnh trong `template.json`, dùng hạt giống là mã cảnh; bắt đầu và dừng mềm |
| `frame` | `'auto'` hoặc `{x, y}` (0–1) | `'auto'` | vị trí chủ thể; `auto` theo phân bố ô nét của cỡ cảnh |
| `trans` | `'cut'`, `'streak'`, `'dip'`, `'fade'` | `'cut'` | chuyển cảnh vào cảnh này, độ dài theo `template.json → transitions`; `plan.check` báo lỗi khi `fade` > 2 |
| `gfx[].icon` | tên trong `catalog.icons` | không | hình ẩn dụ vẽ bằng code trên thẻ `stat` |
| `gfx[type=end-choice].cast` | danh sách `who` | 4 người của phim | dàn nhân vật 3D thật đứng sau thẻ cuối |

## Trang xuất thêm

| Biến | Giá trị |
|---|---|
| `window.CAST` | `[[t0, t1, id, số người trong khung]]`, cho luật `still_person` |
| `window.MOVES` | `[[t0, t1, id, loại máy, số động tác]]`, ghi lại lựa chọn `auto` để người làm phim đọc |

## Âm thanh và nhịp đọc (`kit/sound/`, Python, chạy ngoài trang)

| Tệp | Việc |
|---|---|
| `timing.py` | `schedule(lines, words, template)` → mốc từng dòng theo nhịp đọc của `template.json → voice`; thay các hằng số tự đặt trong `build_plan.py` |
| `score.py` | `compose(beats, template, dur, seed)` → `music.wav` 48 kHz, soạn bằng `core/audio/sampler.py` của thư viện theo `template.json → beats.<nhịp>` (tempo, độ dày, lên, lặng); mức so với giọng theo `sound.music_under_voice_db` |
| `sfx.py` | `place(events, template)` → tiếng động theo sự kiện (`pop`, `count`, `streak`, `whoosh`, `step`) bằng `core/audio/sfx.py` |
| `mix.py` | trộn giọng, nhạc, tiếng động; giảm nhạc khi có lời; −14 LUFS |

## Tất định

- `render(t)` chỉ phụ thuộc `t`, bảng cảnh và hạt giống.
- Chớp mắt, thở, mấp máy và `auto` đều tính lại từ `t`, không giữ trạng thái giữa hai khung.
- Test: gọi `render` theo thứ tự đảo rồi so ảnh băm với thứ tự xuôi.
