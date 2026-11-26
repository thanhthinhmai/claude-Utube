# Research: Âm thanh theo shot (037)

## R1. Phụ thuộc 035 và thứ tự làm

- **Decision**: 037 tách từ `origin/main` (f9cf3f7). Những phần không cần 035 làm trước: kho tiếng (US2), học tiếng (US4), lõi lập/đặt/trộn tiếng (US1) chạy trên tệp `timing.json` và `animatic/keys.json` theo đúng định dạng của 035 (data-model 035). Phần cắm vào bước, điểm duyệt và trang (US1 trên phim thật, US3) làm sau khi 035 merge: rebase 037 lên main mới rồi làm tiếp. Khi phim chưa có hai tệp đó (phim AE cũ), lõi rơi về `out/render-shots.json` / `shots.json` để lấy thời lượng và về mốc câu cho tiếng (không có mốc chuyển động).
- **Rationale**: 035 đang làm ở worktree khác, chưa commit code; sửa chung `build_core.jsx`, `points.py`, `steps.py`, `app.js` sẽ xung đột. Đọc tệp theo định dạng đã chốt trong data-model 035 thì không cần code của 035.
- **Alternatives**: tách từ nhánh 035 (code chưa có, nhánh còn đổi); đợi 035 merge mới bắt đầu (mất thời gian vô ích).

## R2. Mục lục kho tiếng, không có AI lên âm thanh Sonniss

- **Decision**: `soundlib.py` (thư viện chuẩn) quét các thư mục người dùng chỉ ra, đọc **chỉ** tên tệp, đường dẫn thư mục, header WAV (độ dài, kênh, tần số) và metadata chữ trong tệp: chunk `bext` (Description), `LIST/INFO` (INAM, ICMT, IKEY, ISBJ), `iXML` (USER/CATEGORY, UCS `CatID`), ID3/Vorbis cho mp3/ogg/flac nếu có. Sonniss dùng tên kiểu UCS `CATsub_Descriptor_...`; bảng `UCS_CAT` (~80 danh mục UCS) đổi `CatID` thành loại/loại con. Lưu vào SQLite với bảng FTS5 (`name, category, subcategory, description, keywords, folder`). Khoá lập lại: `(path, size, mtime_ns)`; chỉ đọc tệp mới/đổi, xoá mục của tệp đã mất (FR-011, SC-007). Nguồn = `Sonniss GDC <năm>` lấy từ tên thư mục gói, giấy phép `sonniss-gdc-2.0`.
- **Rationale**: giấy phép Sonniss 2.0 cấm dùng tiếng cho AI (FR-013b); tên và metadata Sonniss đủ giàu để tìm theo chữ; FTS5 có sẵn trong sqlite3 của Python, nhanh với 10⁵ mục, không thêm phụ thuộc.
- **Alternatives**: nhúng CLAP cho mọi tệp (cấm theo giấy phép, chậm); chỉ tìm theo tên tệp bằng glob (không xếp hạng, không đọc mô tả).
- **Vị trí**: `$STUDIO_DATA/sound/library.db` (app; mặc định `~/.local/share/claude-utube`), CLI dùng cùng chỗ (`STUDIO_DATA` hoặc mặc định). Danh sách thư mục ở `sound/roots.json`. Không bao giờ trong repo.

## R3. Tìm tiếng cho một hành động

- **Decision**: Claude (Opus 5.5, trong việc làm phim) viết cho mỗi tiếng một `query` chữ tiếng Anh (vd. "glass window shatter") và một loại UCS gợi ý (vd. `GLASS`). `soundlib.search(query, cat, scope)` = FTS5 `bm25` trên các cột (trọng số name 3, description 2, keywords 2, category 1), cộng điểm khi loại khớp, trừ điểm khi độ dài tệp lệch xa độ dài cần (`dur_hint`). Trả 8 kết quả; cái đầu được chọn, 3–7 cái sau là "thay thế cùng loại" cho trang Sound (FR-025). Chỉ chữ (tên, mô tả) đi tới Claude, không âm thanh.
- **Rationale**: tìm chữ, giải thích được, không AI lên âm thanh; Claude giỏi đặt từ khoá theo cách tên Sonniss/UCS viết.
- **Alternatives**: để Claude đọc danh sách tệp và chọn (tốn token, chậm với 10⁴ tệp).

## R4. Freesound chỉ CC0

- **Decision**: Freesound API v2, xác thực bằng token (khoá API miễn phí). `GET /apiv2/search/text/?query=…&filter=license:"Creative Commons 0" duration:[0.2 TO 30]&fields=id,name,tags,description,license,username,duration,previews,url`. Token không tải được tệp gốc (cần OAuth2), nên tải **bản xem trước chất lượng cao** (`preview-hq-ogg`, ~192 kbps) — đủ cho tiếng động trong phim nén AAC 192 kbps. Kiểm lại `license` của từng kết quả trước khi tải (từ chối nếu khác CC0 dù bộ lọc đã lọc). Lưu vào `$STUDIO_DATA/sound/freesound/<id>.ogg` + một mục trong mục lục (nguồn `Freesound #<id> by <user>`, đường dẫn trang, giấy phép `cc0-1.0`, ngày tải). Tự động khi kho trên máy không có kết quả có điểm ≥ ngưỡng (FR-013).
- **Khoá**: như ElevenLabs (036 R3): trong app, khoá mã hoá trong `secrets/freesound.json`, chỉ proxy đọc; việc gọi `POST /internal/sound/freesound` qua proxy. Dòng lệnh: `FREESOUND_API_KEY` trong môi trường hoặc `.env`. `voicekeys.py` được tổng quát cho tên khoá (`elevenlabs`, `freesound`) thay vì sao chép.
- **Rationale**: CC0 không ràng buộc; OAuth2 cần người dùng đăng nhập trình duyệt mỗi lần hết hạn, quá nặng cho lợi ích nhỏ.
- **Alternatives**: OAuth2 để lấy tệp gốc (phức tạp, Complexity); CC BY (người dùng chỉ cho CC0).

## R5. Phạm vi Sonniss: chỉ phim của chủ xưởng

- **Decision**: Trong app, việc của agent **không đọc kho trực tiếp**: mọi tìm và lấy tiếng đi qua proxy (`/internal/sound/search`, `/internal/sound/fetch`). Proxy biết chủ của việc (`jobs.owner` → `accounts.role`): `admin` (chủ xưởng, kể cả Client cùng nhóm) → phạm vi `all`; `customer` → phạm vi `cc0` (chỉ mục Freesound). `fetch` chép tệp đã chọn vào `films/<phim>/sound/cache/<entry>.<ext>` để trộn (phim tự đủ, ổ ngoài rút ra vẫn trộn được). Trang Sound phát thử tiếng thay thế qua `GET /api/sound/preview/{entry}` cũng kiểm phạm vi. Dòng lệnh (không app) = chủ xưởng, phạm vi `all`.
- **Rationale**: FR-013a; giấy phép cấm cung cấp tiếng "như đầu ra của dịch vụ"; kiểm ở một chỗ (proxy) dễ test.
- **Alternatives**: cho agent đọc thư mục kho (sandbox bubblewrap cho đọc khắp nơi, không chặn được theo khách).

## R6. Danh sách tiếng và neo vào chuyển động

- **Decision**: `films/<phim>/sound/plan.json` (data-model). Mỗi tiếng neo vào một trong: `{"motion": "Hand R · Rotation", "edge": "start|end", "offset_f": n}` (từ `animatic/keys.json` của 035: `{shot: [{layer, prop, t0, t1}]}`), `{"line": "l07", "word": "window", "offset_f": n}` (từ `voices/words.json`), hoặc `{"shot_at": 0.35}` (tỉ lệ trong shot), hoặc `{"span": "shot"}` (tiếng nền suốt shot). `soundplan.resolve()` tính mốc tuyệt đối = `t0(shot)` từ `timing.json` + mốc neo, làm tròn khung (FR-003, SC-001). Neo `motion` không còn trong `keys.json` sau khi cắt, hoặc mốc ≥ độ dài shot mới → `state: dropped, why` (FR-004). Claude viết danh sách bằng lệnh `sound cue add` (không sửa JSON tay), sau khi đọc `SCRIPT.md`, `keys.json`, và phần tiếng của phong cách.
- **Rationale**: mốc tương đối đi theo thời lượng shot; `keys.json` có tên chuyển động thật từ AE.
- **Alternatives**: Claude đọc `shots.jsx` và đoán mốc (sai khi biểu thức/ease); mốc tuyệt đối (vỡ khi shot đổi).

## R7. Trộn: tách lớp, giữ nguyên ngoài đoạn sửa

- **Decision**: `soundmix.py` (chạy bằng python của venv thư viện, numpy + soundfile, như `mix.py` hiện nay; không import code của `lib/`) làm `out/mix.wav` từ: giọng (`narration.json` + `voices/*.wav`), nhạc (`out/music.wav` nếu có; `mix.py` của phim AE chỉ còn làm nhạc), các tiếng theo `plan.json`. Mỗi tiếng: đọc tệp cache, đổi về 48 kHz stereo, cắt độ dài, fade vào 5 ms, fade ra theo luật cắt (`cut: hard` = 10 ms tắt ngay tại điểm cắt, `cut: fade` = theo `fade_s`, `cut: over` = kéo qua), gain = `gain_db` so với mức giọng. Ducking nhạc theo đường bao giọng cửa sổ 50 ms (hữu hạn). Khoảnh khắc lặng: nhân mọi lớp (trừ giọng nếu đang nói) với mức `silence_db` trong khoảng, dốc 30 ms. Độ to: một gain cho cả phim tính từ giọng + nhạc (không tính tiếng và lặng) về −14 LUFS (BS.1770, đúng mức kiểm khi giao của `runner/worker.py`), rồi limiter true-peak −2,5 dBTP (soi đỉnh ở 4× lấy mẫu, nhìn trước 5 ms, chỉ ảnh hưởng 7,5 ms quanh đỉnh; AAC cộng thêm ~1 dB nên bản mp4 vẫn ≤ −1 dB). Không dùng compressor có release, nên một sửa chỉ đổi mẫu trong [mốc − 60 ms, kết thúc + 60 ms] (FR-026, SC-006). (Bản đầu dùng soft-clip tanh từng mẫu và không chỉnh độ to: phim thật ra −19 LUFS và đỉnh giữa mẫu +0,8 dB, trượt kiểm khi giao; sửa ở T055.) Mỗi lần trộn ghi `sound/stems/fx.wav` để trang tính khác biệt.
- **Rationale**: SC-006 đòi giống hệt ngoài đoạn sửa; compressor có trạng thái làm lan thay đổi.
- **Alternatives**: ffmpeg `amix` + `sidechaincompress` (có trạng thái, khó chứng minh); tiếp tục để Claude viết `mix.py` riêng (là vấn đề 037 sửa).
- **Kiểm độ lớn**: bước kiểm phim hiện có (`qc.py`/`rhythm.py`) đo `out/mix.wav` như mọi bản trộn (FR-008, SC-009).

## R8. Học tiếng: tách lớp và hai bộ phân loại

- **Decision**: lệnh `learn sfx <set> [--only v01]` (style-learn), tự chạy sau `learn sound` trong luồng học phong cách mới (skill style-learn), chạy riêng được cho phong cách đã có (FR-023). Các bước cho mỗi video (chỉ trên máy):
  1. Demucs `htdemucs` (CPU) tách `vocals`, `drums`, `bass`, `other`. Lớp **tiếng động** = drums + other (bass bỏ vì nhạc); lớp **giọng ngoài lời** = vocals với các khoảng từ của người kể (`profile/<v>/words.json`, nới ±80 ms) bị tắt.
  2. Tìm sự kiện trên cả hai lớp: đường bao RMS 20 ms, khởi âm theo spectral flux (cùng ngưỡng MAD của `soundcraft.sfx_onsets`), sự kiện = đoạn từ khởi âm tới khi RMS rơi dưới −40 dB so với đỉnh hoặc tới khởi âm sau, dài 0,1–8 s; gộp sự kiện cách < 150 ms.
  3. Mỗi sự kiện (cắt từ lớp tìm thấy): AST `MIT/ast-finetuned-audioset-10-10-0.4593` cho top-5 nhãn AudioSet (527); CLAP `laion/larger_clap_general` zero-shot trên danh sách đóng = các nhãn AudioSet thuộc nhóm tiếng động/tiếng người không phải lời (bỏ Speech, Music và con của chúng) viết thành câu "the sound of {label}".
  4. **Đồng ý** khi nhãn top-1 của CLAP nằm trong top-5 của AST, **hoặc** hai nhãn top-1 có cùng tổ tiên ở mức 2 trong cây ontology AudioSet (vd. "Shatter" và "Glass" cùng dưới "Glass"/"Breaking"). Bảng cây được lưu kèm kết quả (FR-018: "bảng tương ứng nhãn ghi trong kết quả học"). Không đồng ý → `unsure`. Ngưỡng tối thiểu: AST xác suất ≥ 0,10 cho nhãn được dùng.
  5. Ghép từ: từ gần nhất có |mốc từ − khởi âm| ≤ 1,0 s (ưu tiên từ đứng trước); không có thì ghép shot (từ `profile/<v>/shots.json`).
  6. Lặng có chủ ý: đoạn ≥ 0,6 s trên lớp tiếng động có RMS ≤ −50 dBFS, bắt đầu ≤ 1 s sau một từ (dung sai 0,2 s cho đuôi từ nhỏ; ghi từ đó và mức dB), và thấp hơn lớp quanh nó 15 dB **hoặc** cả bản trộn cũng ≤ −50 dBFS trong đoạn đó (phim có nhạc vốn đã rất nhỏ: lớp tách không bao giờ hạ 15 dB). 0,4 s bắt cả chỗ ngắt hơi của người kể.
  7. Kết thúc ở điểm cắt: sự kiện có đuôi chạm một điểm cắt (±0,1 s) → `cut: hard` nếu RMS rơi ≥ 20 dB trong 50 ms quanh điểm cắt, `fade` kèm thời gian nếu không, `over` nếu kéo qua > 0,3 s.
  Ghi `profile/<v>/sfx.json`. Tổng hợp phong cách: `sfx_summary` → khối `sound.sfx` trong `kit/template.json` của phong cách và một đoạn trong mục âm thanh của `STYLE.md`, mỗi luật kèm mốc bằng chứng (FR-021). Không ghi âm thanh nào vào phong cách (FR-022); các lớp tách ra nằm ở `references/<set>/stems/` (ngoài git) và bị xoá khi `--clean`/dịch vụ online xoá video.
- **Chỉnh sau lần chạy thật T040 (2026-11-26, người dùng chọn "hai mức tin")**:
  - Lớp không giọng = drums + **bass** + other: lặng có chủ ý đo trên lớp này (trong phim giọng vẫn còn lúc lặng), và phải thấp hơn mức xung quanh (±5 s, p75) ≥ 15 dB; trên bản trộn gốc nhạc che mất khoảng lặng.
  - Mỗi khởi âm mạnh (tăng ≥ 3 dB so với 60 ms trước) mở một sự kiện mới, sự kiện dừng ở khởi âm kế tiếp; phân loại trên cửa sổ cố định [t − 0,1; t + 1,0] s (đoạn quá ngắn AST không nghe ra, đoạn dài là nhạc nền).
  - CLAP chọn trong danh sách **câu mô tả** (`audioset.PHRASES`, mỗi câu gắn nhãn AudioSet → nhóm mức 2) thay cho 369 nhãn AudioSet; nhãn Speech/Music của AST không bao giờ gọi tên tiếng động.
  - **Hai mức tin** thay cho "chỉ tin khi đồng ý": `sure` khi nhóm của câu CLAP gặp nhóm một nhãn AST p ≥ 0,10; `likely` khi CLAP được một nhãn AST p ≥ 0,03 cùng nhóm đỡ, hoặc CLAP ≥ 0,9, mà AST không nêu nhóm khác ≥ 0,25; hoặc AST top ≥ 0,15 mà CLAP không nêu nhóm khác ≥ 0,5. Lý do (đo trên voice-check): CLAP nghe đúng bọt nước 0,74, bóng rổ 0,94, đám đông 0,96 trong khi AST ở đó < 0,10; AST nghe đúng kính vỡ ("Smash, crash" 0,18) trong khi CLAP sai. Luật đồng ý nghiêm chỉ bắt 1/5 tiếng kỳ vọng. Mỗi mục trong `sound.sfx.actions` ghi `trust` và `n_sure`.
- **Kết quả T040 (2026-11-26, hai mức tin)**: 724 sự kiện, 289 được tin (78 `sure`, 211 `likely`), 53 lặng chọn. SC-003 **2/5, chưa đạt** (cần ≥ 4/5): lặng tìm thấy (6,22 s, −63 dB), bóng tìm thấy (161,8 s, `sure` "ball bouncing"). Trượt: kính vỡ (cả hai bộ nghe thành tiếng kim loại: AST "Chink, clink"/"Coin (dropping)", CLAP "coins dropping"/"keys jangling", nhóm không khớp Glass); bọt nước tìm ở 25,18 s (`likely` "aquarium bubbles", 0,18 s sau cửa sổ [21,5; 25,0]) và 16,3 s; đám đông tìm ở 163,46 s (`likely` "crowd cheering" trong lớp giọng ngoài lời, 0,54 s trước cửa sổ [164; 168,5]). Không nới cửa sổ kỳ vọng cho vừa kết quả: cửa sổ ghi theo tai trước khi chạy. Nhiều nhãn `likely` sai ("zipper", "alarm" trên nhạc nền) → đề xuất: kế hoạch tiếng chỉ tự dùng mục `sure`, mục `likely` chỉ là gợi ý.
- **Bài chấm khớp hình bằng tiếng CC0 (2026-11-26)**: bài chấm có đáp án phải dùng tiếng **không phải Sonniss** (FR-013b cấm mô hình AI nghe âm thanh Sonniss; hai bài chấm đầu lỡ dùng bản trộn có tiếng Sonniss, kết quả đã xoá) và tiếng phải **khớp hình** (chèn tiếng ngẫu nhiên như chó sủa, súng vào phim không có chúng thì điểm không nói gì). Bài chấm: bản sao `ae-sleepless-test`, 9 tiếng Freesound CC0 neo theo chuyển động (đồng hồ, pop, dế, vải, bút chì, chim, chuông, ngáp, phất áo) + 2 khoảng lặng. Kết quả: `sure` 2 (1 đúng: đồng hồ; 1 sai: "car horn"), `likely` ~6 (gần đúng 1–2: vải → "paper rustling"/"Zipper (clothing)"), tổng ~1,5/9. Mỗi bộ đúng ở chỗ khác (AST nghe đúng dế 0,41, CLAP nghe đúng chuông 0,80 đúng mốc) nhưng bất đồng nên bị bỏ; tiếng foley nhỏ dưới giọng và nhạc ở sát giới hạn của cả hai.
- **Chỉnh sau bài chấm**: (1) bỏ luật "AST thắng khi bất đồng" (đặt nhãn sai: giấy → "camera", phất áo → "gasp"); (2) AST chỉ nghe lớp mà sự kiện được tìm thấy (tiếng động trên lớp tiếng động, sự kiện giọng trên lớp giọng), không nghe bản trộn (hơi thở người kể thành "Gasp", nốt piano thành "Explosion"); (3) lặng: ≥ 0,6 s và nhánh "cả bản trộn im" (mục 6). Voice-check sau chỉnh: **3/5** (kính vỡ, lặng, bọt nước; trước 2/5), `likely` 189 → 129, `sure` 46 → 41. SC-003 **vẫn chưa đạt** (cần 5/5).
- **Quyết định (người dùng, hướng A)**: dừng tinh chỉnh phần nhận tên tiếng. `sound.sfx → actions` chỉ giữ tiếng `sure`; tiếng chỉ một bộ nghe ra vào `hints` (gợi ý, Claude chỉ dùng khi hình có tiếng đó). Các số không cần tên tiếng (mật độ, độ lớn so với giọng, lặng, luật cắt) dùng như cũ. Claude chọn tiếng theo hình (`tools/ae/SOUND.md`), người dùng duyệt từng shot.
- **Rationale**: đúng phương pháp đã kiểm bằng tay trên mẫu voice-check (đám đông trong lớp giọng; CLAP tự tin quá mức trên danh sách đóng nên cần AST đồng ý).
- **Alternatives**: chỉ AST (nhầm nhãn với tiếng chồng nhạc); chỉ lớp tiếng động (bỏ sót đám đông, đã chứng minh).
- **Hiệu năng**: CPU (WSL không có GPU NVIDIA). Ước tính video 3 phút: Demucs ~2–4 phút, AST+CLAP ~1 s/sự kiện. Chấp nhận được vì học chạy nền. GPU chỉ bắt buộc cho dựng hình (memory "GPU render only"), không cho học.

## R9. Tầng phụ thuộc `deps sound`

- **Decision**: `tools/requirements-sound.txt`: `torch` (bản CPU, `--index-url https://download.pytorch.org/whl/cpu`), `demucs`, `transformers`, `soundfile`. Cài bằng `sh bin/studio deps sound` vào `tools/.venv` (gói Python, không phải phần mềm hệ thống; hiến pháp cho phép). Mô hình tải về bộ nhớ đệm Hugging Face lần đầu dùng (đã có sẵn trên máy phát triển). Bộ cài app (016) **không** chứa tầng này ở bản này; app báo "Sound learning needs: sh bin/studio deps sound" khi thiếu. Giấy phép ghi CREDITS: PyTorch BSD-3, Demucs MIT (mô hình htdemucs MIT), Transformers Apache-2.0, AST (thẻ mô hình BSD-3-Clause), CLAP larger_clap_general (Apache-2.0), nhãn/ontology AudioSet CC BY 4.0 (Google). Kiểm lại từng thẻ mô hình khi cài (T-task).
- **Rationale**: tách tầng để bộ cài không phình ~1 GB; chỉ người học phong cách mới cần.

## R10. Điểm duyệt Sound và đồ thị

- **Decision**: giữ tên điểm `mix` (035 đổi tên hiện thành "Sound" cho phim AE). Với phim AE, `points.stale("mix")` thêm `sound/plan.json`, `timing.json`, `narration.json` vào danh sách tệp mới hơn `out/mix.wav`; `fingerprint("mix")` thêm băm `sound/plan.json` + `sound/notes.json` (ghi chú mở). `ae render` (bản đẹp) gọi `points.gate(d, "mix")` sau cổng animatic của 035 (FR-028). Đồ thị bước đã có (035): Animatic → Mix (Sound) → Render (Final render). Sửa ở trang Sound chỉ chạy lại trộn và ghép tiếng (`mux`), không dựng hình (như specs/026).
- **Ghi chú/sửa nền**: `sound/notes.json` dùng `pins.py` của 035 (ghi chú chung theo shot, không cần ghim x/y); "Send notes to Claude" = quyết định `revise` của yêu cầu duyệt `mix` trong việc đang chạy, hoặc việc `fix` `target: "sound"` ngoài việc (như 032/034/035).

## R11. Không để lọt âm thanh tham chiếu

- **Decision**: (a) `soundlib` từ chối chỉ mục bất kỳ thư mục nào nằm dưới `references/` hoặc `$STUDIO_DATA/learn/`; (b) `soundplan` chỉ nhận mục có `source` ∈ {sonniss, freesound, user}; (c) test tự động: trộn một phim thử với một kho có lẫn tệp từ `references/` → lỗi; (d) `.gitignore` có `sound/cache/`, `references/*/stems/`; test repo kiểm 0 tệp âm thanh mới ngoài các fixture nhỏ tự tổng hợp (SC-005).

## R12. Đo SC-003 trên mẫu đã kiểm

- **Decision**: `references/voice-check/a.wav` + câu có mốc `segs.json` (đã có, chỉ trên máy). Quickstart chạy `learn sfx --file references/voice-check/a.wav --words …` (chế độ tệp rời, không cần bộ tham chiếu đầy đủ) và so với 5 sự kiện kỳ vọng ghi trong `tests/learn/data/voicecheck_expect.json` (chỉ mốc và nhãn, không âm thanh). Test tự động trong `tests/learn` dùng âm thanh tổng hợp (tiếng vỡ = nhiễu trắng có đường bao, đám đông = nhiễu màu hồng điều biên) và **giả** hai bộ phân loại (để test luật đồng ý, lặng, cắt) vì mô hình nặng không chạy trong bộ test thường.
