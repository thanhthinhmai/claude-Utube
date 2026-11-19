# Contract: CLI

Mọi lệnh có `--json` in một đối tượng JSON ra stdout. Lỗi in một dòng `✗ …` ra stderr kèm lệnh cần chạy.

## `sh bin/studio point`

| Lệnh | Việc làm | Mã thoát |
|---|---|---|
| `point status <phim> [--json]` | Trạng thái năm điểm (`on`, trạng thái, dấu hiện tại, lần duyệt) và mười bước (`steps.status`) | 0 |
| `point set <phim> <điểm,…\|none>` | Đổi `reviews.on` của phim; từ chối nếu muốn đổi một điểm đang `approved` hay `waiting` | 0 / 2 |
| `point approve <phim> <điểm> [--base F] --source chat\|ui\|api [--by X] [--review R]` | Kiểm như R3, rồi ghi lần duyệt. Không có `--base` thì lấy dấu hiện tại (chỉ dùng cho `chat`) | 0 đạt · 1 phép kiểm chưa đạt · 4 `base` cũ |
| `point gate <phim> <điểm>` | In lý do bị chặn (mỗi dòng một lý do), không có lý do thì không in gì | 0 / 1 |

Cổng nằm trong các lệnh có sẵn:

- `voice make <phim>`: chặn khi cổng `script` có lý do. Bỏ qua bằng `--skip-review "<lý do>"` (ghi vào `reviews.skipped`).
- `voice make <phim> --only L09,L10`: chỉ tạo lại các dòng đó (R8).
- `voice make <phim> --changed`: chỉ tạo lại các dòng có chữ, `say`, giọng hoặc tốc độ khác lần tạo trước (theo `voices/.made.json`) hoặc thiếu `wav` (R7).
- `render <phim>`: `render-gate` chặn thêm theo cổng `shots`. `--skip-checks "<lý do>"` bỏ qua cả cổng này và được ghi lại.
- `qc shots <phim> --only S012[,S013]`: chỉ vẽ ảnh xem trước, không ghi kết quả tầng (R10).

## `sh bin/studio edit <phim> <thao tác> … --base <dấu> [--by X] [--source ui|chat|api] [--json]`

| Thao tác | Đối số | Kiểm hợp lệ (sai thì không ghi gì) | Chạy sau khi lưu |
|---|---|---|---|
| `script-para` | `<P#> --text-file <tệp>` | `P#` có trong `SCRIPT.md`; chữ không rỗng, ≤ 4000 ký tự, không chứa `[P` | `script check` |
| `voice-say` | `<L#> --say "<chữ>"` (rỗng là xoá) | dòng có trong `lines.json`; ≤ 400 ký tự | — |
| `voice-remake` | `<L#>` | dòng có trong `lines.json` | `voice make --only`, `voice asr` và `qc voice` cho dòng đó |
| `voice-set` | `voice=<v> speed=<s> --confirm all` | giọng của thư viện; tốc độ trong [0.7, 1.3] | `voice make` cả phim, `voice asr`, `qc voice` |
| `shot` | `<S#> [set=…] [cam=…] [act=…]` | phim có `scenes.json`; `scenecheck` đạt trên bản tạm | `qc plan`, `qc shots --only <S#>` |
| `shots-check` | — | — | `qc shots` đầy đủ |
| `except` | `<S#> <luật> --reason "…"` | lý do không rỗng; cảnh và luật có trong kết quả tầng | `qc except` |
| `accept-style` | `--reason "…"` | lý do không rỗng | `qc accept-style` |
| `mix` | `[music=seed:N\|none] [under=dB] [between=dB] [sfx=dB]` | trong dải của R11 | `mix.py`; ghép tiếng lại nếu đã có video |
| `publish` | `[chosen=1..3] [description-file=…] [hashtags=a,b,c]` | chọn trong 1..3; 3–5 hashtag | `publish --check-only` |

Mã thoát: 0 lưu và kiểm đạt · 1 lưu được, kiểm chưa đạt · 2 không hợp lệ, không ghi gì · 4 `base` khác dấu hiện tại · 5 bận (`busy.json` còn sống, chặn bước này).

JSON in ra: `{"ok", "code", "op", "point", "ref", "fingerprint": <dấu mới của điểm>, "check": {…kết quả tóm tắt…}, "stale": ["Voice", …], "files": ["… ảnh mới …"], "error": "…"}`.

## `channel set <kênh> reviews <điểm,…|none>`

Ghi `reviews` vào hồ sơ kênh. Điểm phải thuộc năm điểm. `channel show` in dòng `reviews: script, shots`.

## `job start --kind film … [--points script,shots]`

Ghi `reviews.on` của phim khi đã có thư mục phim. Không có `--points` thì dùng mặc định của kênh hoặc của xưởng.

## `review request <job> --kind script|voice|shots|mix|publish --film <phim> --summary <tệp>`

Như specs/003: việc chuyển sang `waiting_review`, bước hiện là `Waiting for <kind> review`. Online thì agent kết thúc lượt; luồng chat thì gọi `review wait`.

## Agent: luồng chat (CLAUDE.md)

Ở mỗi điểm duyệt đang bật (kiểm bằng `point status <phim> --json`):

- **Có giao diện**: `review request … --kind <điểm> --film <phim>`, báo người dùng đường dẫn, rồi `review wait`. Duyệt thì làm tiếp. `revise` thì sửa theo ghi chú rồi gửi lại.
- **Không có giao diện**: hỏi người dùng trong chat. Đồng ý thì `point approve <phim> <điểm> --source chat`.
- **Sau khi duyệt**: chạy `point status`, rồi làm lại các bước `stale` theo thứ tự của đồ thị trước khi đi tiếp.
