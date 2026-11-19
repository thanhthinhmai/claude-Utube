# Research: Điểm duyệt và chỉnh sửa trên trang việc làm phim

## R1. Lần duyệt lưu ở đâu

- **Decision**: lưu trong thư mục phim, ở `checks.json` → `reviews` (qua `report.update`). Studio ghi vào đó khi duyệt (gọi `filmcheck.points.approve`); luồng chat không có giao diện thì ghi bằng `sh bin/studio point approve`.
- **Rationale**: cổng (`voice make`, `render-gate`) nằm trong `filmcheck` và phải chạy được khi không có giao diện, kể cả trong container online. `checks.json` đã là nơi giữ kết quả các tầng, và nó không tính vào dấu nội dung (`tiers.SKIP_NAMES`).
- **Alternatives**: chỉ lưu trong sổ việc của studio, nhưng khi đó cổng phải gọi studio và không chạy được khi chưa cài giao diện. Một tệp riêng `reviews.json`: thêm một tệp mà không được gì thêm.

## R2. Dấu nội dung theo phần

- **Decision**: mỗi điểm có một tập tệp, và dấu của điểm là SHA-256 (16 hex) trên tập đó, cùng cách tính của `tiers.fingerprint`:
  - `script`: `SCRIPT.md`, `SOURCES.md`;
  - `voice`: `lines.json`, `voices/*.wav` (đúng phần `voice` hiện có);
  - `shots`: dấu `all` của `tiers` (cùng dấu mà `qc plan` và `qc shots` ghi), với `mix.json` được thêm vào danh sách bỏ qua;
  - `mix`: `mix.json`, `out/mix.wav`;
  - `publish`: `publish/pack.json`.
- **Rationale**: duyệt Shots phải mất hiệu lực đúng khi kết quả tầng 1–2 mất hiệu lực, nên dùng cùng dấu. Đổi bản trộn hay gói đăng thì không đụng dấu hình, vì `out/` và `publish/` đã bị bỏ qua, còn `mix.json` được thêm vào. `tools/render/lib.mjs` có cùng danh sách bỏ qua và phải đổi theo.
- **Alternatives**: dấu theo đồ thị phụ thuộc đầy đủ (dấu của bước gồm dấu các bước trước). Cách này chính xác hơn nhưng phức tạp, và dấu `all` đã bao phủ phần hình.

## R3. Duyệt gắn với nội dung nào

- **Decision**: duyệt gắn với nội dung **lúc bấm duyệt**. Trang gửi `base` (dấu của điểm mà trang đang hiện). Máy chủ chỉ nhận khi `base` bằng dấu hiện tại **và** phép kiểm của điểm đạt trên nội dung hiện tại:
  - script: `script check` đạt;
  - voice: `qc voice` đạt;
  - shots: `qc plan` và `qc shots` đạt với dấu hiện tại, không còn cảnh báo chưa chấp nhận;
  - mix: bản trộn mới hơn `mix.json`;
  - publish: `publish --check-only` đạt.
- **Rationale**: chủ phim thường sửa rồi mới duyệt, nên dấu lúc gửi yêu cầu duyệt đã cũ. Điều kiện `base` bằng dấu hiện tại chặn việc duyệt một nội dung mình chưa thấy (FR-025).
- **Alternatives**: gắn với dấu lúc gửi yêu cầu duyệt, nhưng như vậy mọi lần sửa đều phải gửi yêu cầu duyệt mới.

## R4. Bật hoặc tắt điểm duyệt

- **Decision**: hồ sơ kênh có `reviews: ["script","shots"]` (mặc định khi chưa đặt). `channel attach` chép nó vào `checks.json` → `reviews.on` của phim. Phim không có kênh thì dùng mặc định của xưởng (`script`, `shots`). Muốn đổi cho riêng phim: `sh bin/studio point set <phim> script,shots,voice`, hoặc `PUT /jobs/{id}/points`; chỉ được bật hay tắt điểm chưa được duyệt.
- **Rationale**: không lưu trong `channel.json` của phim, vì tệp đó nằm trong dấu `all`, nên bật tắt một điểm sẽ làm mất duyệt Shots. `checks.json` thì nằm ngoài dấu.

## R5. Cổng

- **Decision**: `points.gate(film_dir, point)` trả danh sách lý do (giống `tiers.gate`).
  - `voice make` gọi cổng `script` trước khi chạy `tts.py`;
  - `render-gate` gọi `tiers.gate` rồi cổng `shots`;
  - `job done`, publish và mux **không** có cổng (duyệt Mix và Publish chỉ dừng agent, không chặn lệnh).
  - Điểm tắt thì cổng trả `[]`. `--skip-checks "<lý do>"` của render bỏ qua cả cổng `shots` và được ghi lại (FR-021).
  - `voice make` có thêm `--skip-review "<lý do>"`, cũng được ghi lại.
- **Rationale**: chỉ chặn ở hai chỗ đắt nhất. Mix và Publish không có bước tốn kém nào phía sau.

## R6. Thao tác sửa: một lệnh, nhiều kiểu

- **Decision**: `sh bin/studio edit <phim> <thao tác> [đối số] --base <dấu> --json`. Mọi kiểu thao tác dùng chung một khung:
  1. kiểm khoá bận;
  2. so `base` với dấu của điểm;
  3. kiểm hợp lệ, và **không ghi gì nếu sai**;
  4. ghi qua tệp tạm rồi đổi tên;
  5. chạy lệnh của chính bước đó;
  6. ghi một dòng vào `.check/edits.jsonl`;
  7. in JSON kết quả.

  Mã thoát: 0 đạt, 1 lưu được nhưng kiểm chưa đạt, 2 không hợp lệ (không ghi), 4 xung đột `base`, 5 đang bận.
- **Rationale**: một chỗ duy nhất giữ luật "không ghi khi sai" (FR-005, SC-003). Chat, studio và online đều gọi cùng một lệnh. Dễ test bằng `unittest`.

## R7. Sửa kịch bản và lời đọc

- **Decision**:
  - `edit script-para <P#> --text-file f` thay nội dung đoạn `[P#]` trong `SCRIPT.md` rồi chạy `script check` (theo luật, không gọi Claude). Lượt biên tập không chạy lại (Clarifications).
  - Sau khi duyệt Script, agent dựng lại `lines.json` từ kịch bản như hiện nay. Rồi `voice make --changed`: `voices/.made.json` ghi chữ (hoặc `say`), giọng và tốc độ của mỗi dòng lúc tạo; chỉ dòng khác hoặc thiếu `wav` được tạo lại.
  - Thêm kiểm "lời khớp kịch bản" vào `qc voice` (tầng 0), dùng lại phép so của `qc.py` (FR-007).
- **Rationale**: lời đọc chỉ đi một chiều, từ kịch bản sang `lines.json`. Tạo lại giọng chỉ cho dòng đổi (FR-017, SC-004).

## R8. Làm lại một dòng giọng

- **Decision**: `edit voice-say <id> --say "…"` ghi `say` (rỗng thì xoá). `edit voice-remake <id>` (và `voice make --only`) làm như sau:
  - viết `.say.json` chỉ gồm dòng đó vào thư mục tạm;
  - chạy `tts.py` vào thư mục tạm;
  - chép `<id>.wav` vào `voices/` và gộp `dur.json`;
  - chạy `voice asr` và `qc voice` trên đúng dòng đó (`asr_check.py` với tệp dòng tạm), rồi gộp mốc từ.

  `edit voice-set voice=<v> speed=<s>`: trang phải gửi `confirm=all`. Lệnh ghi `voice` và `speed` cho mọi dòng rồi chạy `voice make` cả phim. Giọng phải nằm trong danh sách giọng của thư viện (`channels.voice_ok`).
- **Rationale**: `tts.py` ghi đè `dur.json` bằng đúng các dòng được đưa vào, nên phải chạy ở thư mục tạm rồi gộp. Không sửa thư viện.

## R9. Bảng cảnh tách ra `scenes.json`

- **Decision**:
  - `film()` của bộ dựng nhận `scenes` là mảng (như cũ) hoặc đường dẫn, mặc định `'./scenes.json'`. Tệp có dạng `{"custom": ["platform"], "scenes": [...]}`.
  - Trang phim vẫn khai báo hàm dựng của các bối cảnh riêng trong `film({custom})`. `film()` báo lỗi nếu tên trong `custom` của tệp không khớp.
  - `scenecheck.mjs` nạp `films/<phim>/kit/plan.js`, chạy `check(scenes)` với danh mục, và in lỗi dạng `"s07: …"`.
  - `edit shot <id> set=… cam=… act=…` sửa đúng cảnh đó, chạy `scenecheck` trên bản tạm, đạt thì đổi tên vào chỗ, rồi chạy `qc plan` và `qc shots --only <id>`.
  - Phim cũ có `SCENES` viết thẳng trong `index.html` vẫn chạy được; khung Shots khi đó chỉ xem, giống phim không có bộ dựng.
  - Danh mục lựa chọn cho trang: `GET /steps` trả `catalog` (bối cảnh, máy, động tác, các tiền tố act) đọc từ `kit/catalog.json` của phim, cộng `custom`.
- **Rationale**: sửa dữ liệu thì không phải sửa mã (FR-009). Kiểm hợp lệ bằng đúng phép kiểm mà trang phim dùng, nên không có hai bộ luật khác nhau (FR-010).

## R10. Ảnh mới cho một cảnh

- **Decision**: `qc shots --only S012,S013` chỉ vẽ ảnh của các cảnh đó vào `.check/shots/` (để xem trước) và **không** ghi kết quả tầng. Nút duyệt Shots chỉ bật khi đã chạy `qc shots` đầy đủ với dấu hiện tại. Trang có nút "Run shot check" (thao tác `edit shots-check`) để chạy lượt đầy đủ.
- **Rationale**: chủ phim thấy ảnh mới trong vòng 2 phút (SC-001), mà cổng vẫn dựa trên lượt kiểm đầy đủ.

## R11. Nhạc và mức tiếng

- **Decision**:
  - `mix.json` có dạng `{"music": "seed:7"|"seed:3"|"seed:11"|"none", "music_under_voice_db": x, "duck_db": y, "sfx_db": z}` (seed 7 là nhạc mặc định của bộ dựng).
  - Dải cho phép lấy từ `template.json` → `sound`: `music_under_voice_db` trong dải đo của phong cách, nới ±3 dB; `duck_db` (nhạc giảm bao nhiêu khi có lời, mặc định −6) trong [−20, 0]; `sfx_db` (tăng giảm hiệu ứng so với mặc định) trong [−24, +6]. Khi làm, "nhạc giữa các nhịp" của spec được hiểu là mức giảm nhạc khi có lời (`duck_db`). Lời luôn chuẩn hoá về `lufs` của phong cách.
  - `mix.py` đọc `mix.json` khi có; không có thì giữ cách cũ. Các lựa chọn nhạc là các `seed` của `score.compose`, và mỗi kiểu chỉ soạn khi được chọn.
  - `edit mix …` ghi `mix.json` rồi chạy `mix.py`. Nếu đã có `out/video.mp4` thì ghép tiếng lại bằng `core/render/mux.sh` của thư viện (gọi, không sửa).
- **Rationale**: bộ âm thanh hiện có một kiểu nhạc với `seed`. Đổi `seed` cho ra bài khác mà không phải viết thêm kiểu nhạc (spec Assumptions).

## R12. Ai chạy thao tác, và chờ duyệt ở chế độ online

- **Decision**:
  - Tài liệu `action` trong sổ việc có các trường `{id, job_id, owner, point, op, args, base, status: queued|running|done|failed, result, created_at}`.
  - Local và app: `actions.py` chạy từng thao tác theo thứ tự cho mỗi việc, trong một luồng nền của máy chủ web: `sh bin/studio edit … --json`, với `cwd` là gốc xưởng.
  - Online: worker lấy các `action` đang `queued` của việc ở trạng thái `waiting_review`, chạy `sh bin/studio edit` trong container của việc (cùng ảnh và cùng thư mục phim), **không** gắn proxy Claude và **không** trừ hạn mức. Container dừng khi hàng đợi thao tác của việc trống.
  - Việc chờ duyệt giữ trạng thái `waiting_review` trong sổ việc. Cơ chế `resume_answered` hiện có đưa việc vào lại hàng đợi, kèm lời nhắn theo loại điểm duyệt.
  - Luồng chat local: agent gọi `review wait`.
  - Mỗi thao tác chạy xong thì ghi một dòng vào nhật ký việc, nên trang nhận sự kiện `job.updated`.
- **Rationale**: dùng lại hàng đợi, container và cách nối lại phiên agent của 007/008 (FR-022, FR-023). Thao tác không cần Claude.
- **Alternatives**: một dịch vụ thao tác riêng. Cách này thêm một tiến trình mà không được gì thêm.

## R13. Khoá bận và hai người cùng sửa

- **Decision**: `.check/busy.json` có dạng `{"step": "Voice", "pid": …, "host": …, "since": …}`. Online, `job run` chạy trong container khác với web và worker, nên khoá khác `host` được coi là còn sống khi chưa quá 6 giờ và việc đang `running` với bước trùng.
  - `edit` tạo khoá trong lúc chạy.
  - `job run` tạo khoá khi việc có `film_dir`, với `step` là tên bước của nó.
  - `edit` từ chối (mã 5) khi khoá còn sống (cùng `host`: pid còn chạy) và bước của khoá nằm trong tập bước mà thao tác đọc hoặc ghi theo `steps.py`.
  - Hai người cùng sửa thì xử lý bằng `base` (mã 4). Trang hiện "Changed since you opened it: reload".
- **Rationale**: FR-024 và FR-025 không cần khoá phân tán. Thư mục phim là một chỗ duy nhất.
