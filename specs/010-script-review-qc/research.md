# Research: Kịch bản được chấm và QC video tự động

Nền: luồng làm phim của thư viện (Treatment → Look → Voice → Music → Picture → Mix → Render → Self-check), hướng dẫn việc online `tools/runner/JOB.md`, cổng QC của 007 (`worker.quality()`), chế độ gói của 008 (mọi lần gọi Claude đi qua `proxy`, container không có internet).

Các mục **Kiểm khi implement** dựa trên hành vi chưa thử. Task đầu tiên PHẢI thử từng mục; kết quả khác thì dừng và hỏi người dùng (hiến pháp II).

## R1. Một bộ công cụ cho cả local và online
- **Decision**: thêm lệnh `sh bin/studio script check|review|status`, `sh bin/studio web fetch` và `sh bin/studio qc`. Agent gọi cùng các lệnh này ở cả hai chế độ:
  - local: luồng làm phim trong `CLAUDE.md`;
  - online: `JOB.md`.

  Phần lõi (chấm, đo) là mã Python của xưởng trong `tools/filmcheck/`, không gọi Claude.
- **Rationale**: test một lần cho cả hai chế độ. Ở chế độ online, worker chạy lại đúng các lệnh này làm cổng QC, nên agent không tự báo đạt được.
- **Alternatives**: viết luật vào lời nhắc để agent tự kiểm: tốn token, không đo được (hiến pháp IV).

## R2. Máy chấm kịch bản
- **Decision**: Python thuần (thư viện chuẩn), đọc `SCRIPT.md` và `SOURCES.md` theo [contracts/files.md](contracts/files.md). Điểm bắt đầu từ 10 rồi trừ theo bảng ở [contracts/cli.md](contracts/cli.md). Các luật:
  - tách câu theo `.?!…` (và `。？！` cho tiếng Trung, tiếng Nhật);
  - đếm từ bằng khoảng trắng; ngôn ngữ không tách từ (zh, ja, ko) đếm ký tự;
  - tốc độ đọc mặc định: en 150 từ/phút, vi 170 âm tiết/phút, zh 4,5 ký tự/giây. Ghi đè được bằng dòng `Speed:` ở đầu kịch bản;
  - hook: trong cửa sổ đầu (30 giây, hoặc 20% thời lượng với phim dưới 30 giây) có câu hỏi, con số, hoặc một từ đảo ý trong danh sách của ngôn ngữ (en: but, yet, actually, never, only, why, what if; vi: nhưng, thật ra, chưa từng, tại sao…). Câu đầu không được là câu chào hay giới thiệu kênh (danh sách mở đầu cấm theo ngôn ngữ);
  - điểm giữ chân: cùng dấu hiệu như hook; khoảng cách giữa hai điểm liên tiếp ≤ 90 giây (chỉ với phim từ 90 giây);
  - câu sáo rỗng: danh sách cụm từ trong `tools/filmcheck/cliches/<lang>.txt` (en, vi);
  - số dễ đọc sai: chữ số ≥ 1000, số thập phân, phần trăm, số thứ tự (3rd), đơn vị viết tắt (km, kg, mph…). Lấy từ luật của `asr_check.py` trong thư viện: các số này Whisper và Kokoro đọc khác bản viết.
- **Rationale**: chạy dưới 1 giây, không mạng, test được bằng kịch bản mẫu (SC-002).
- **Alternatives**: dùng thư viện NLP (spaCy, nltk): thêm phụ thuộc nặng cho một việc tách câu đơn giản.

## R3. Biên tập độc lập
- **Decision**: `script review` tự chạy một tiến trình Claude Code riêng: `claude -p` với lời nhắc và lược đồ trả lời cố định do xưởng viết, `--json-schema`, `--output-format json`, `--no-session-persistence`, `--model` theo cài đặt (R6).
  - Công cụ của biên tập chỉ có `Read`, `Grep`, `WebSearch` và `Bash(sh bin/studio web fetch:*)`.
  - Biên tập chỉ nhận đường dẫn tới `SCRIPT.md`, `SOURCES.md`, `TREATMENT.md` và yêu cầu của phim (`.input.json` online, hoặc `BRIEF.md` local, contracts/files.md). Nó không có lịch sử của agent.
  - Online: tiến trình chạy trong cùng container, với `CLAUDE_CODE_OAUTH_TOKEN` của việc, nên mọi lần gọi đi qua proxy và token được tính vào việc (FR-016). Local: dùng `claude` trên máy của người dùng.
- **Rationale**: tiến trình mới không thấy quá trình viết (FR-007). Lời nhắc nằm trong code của xưởng, nên agent không sửa được. Cách gọi giống `moderation.py` của 008, cách đã chạy thật.
- **Alternatives**: subagent qua công cụ `Agent` trong phiên của agent: agent tự viết lời nhắc cho biên tập, nên tính độc lập phụ thuộc vào agent, và khó test.
- **Kiểm khi implement**: `claude -p` trong container với `CLAUDE_CODE_OAUTH_TOKEN` và `ANTHROPIC_BASE_URL` trỏ tới proxy chạy được cùng lúc với phiên Agent SDK đang chạy (hai tiến trình, cùng mã của việc).

## R4. Tìm và mở trang web (FR-007a)
- **Tìm**: bật công cụ `WebSearch` của Claude Code cho agent (hiện đang bị cấm trong `agent.py`) và cho biên tập. Đây là công cụ chạy phía Anthropic: Claude Code gửi một lệnh gọi `/v1/messages` có công cụ `web_search`, nên lệnh này đi qua proxy như mọi lần gọi khác.
- **Mở trang**: `WebFetch` của Claude Code tải trang ngay trên máy chạy nó. Container không có internet, nên công cụ này không dùng được. Thay bằng `sh bin/studio web fetch <url>`:
  - local: tải thẳng;
  - online: CLI gọi `POST /internal/web/fetch` của proxy (proxy có mạng ra ngoài) bằng mã của việc.
  - Trả về chữ đã bỏ thẻ HTML, tối đa 20 000 ký tự, kèm mã HTTP và URL cuối.
  - Mỗi lần mở được ghi vào `films/<name>/.check/opened.json`. Máy chấm dùng tệp này để kiểm "mọi đường dẫn trong `SOURCES.md` đã mở được" (FR-002).
- **An toàn của `web fetch` ở proxy**:
  - chỉ `http` và `https`, cổng 80 và 443;
  - phân giải tên trước; từ chối địa chỉ riêng, loopback, link-local, đa hướng và mọi địa chỉ của mạng Docker. Mỗi lần chuyển hướng kiểm lại (tối đa 3);
  - tối đa 2 MB và 15 giây mỗi trang, tối đa 60 trang mỗi việc;
  - chỉ nhận `text/html`, `text/plain`, `application/json`, `application/xml`;
  - nhật ký chỉ ghi tên miền và mã HTTP.
- **Rationale**: container vẫn không có đường ra internet (007). Proxy đã giữ mã của việc và đã có mạng ngoài.
- **Alternatives**: cho container ra internet qua bộ lọc `egress` với danh sách mở: mở rộng đường ra cho cả agent, khó giới hạn. `web_fetch` phía máy chủ của API: Claude Code không có công cụ này, còn gọi thẳng Messages API bằng mã của gói thì trái R6 của 008.
- **Chi phí**: lượt tìm qua khoá API dự phòng tính 10 USD cho 1000 lượt. Proxy đọc `usage.server_tool_use.web_search_requests` và thêm vào bảng giá; qua gói thì chỉ đếm.
- **Kiểm khi implement**: `WebSearch` của Claude Code chạy được qua proxy ở chế độ gói (một tài khoản Max), và `web_search_requests` có trong `usage`.

## R5. Mốc thời gian của lời đọc (FR-011)
- **Decision**: agent ghi `films/<name>/narration.json` ([contracts/files.md](contracts/files.md)). Tệp chỉ đường tới `words.json` mà `asr_check.py` của thư viện viết ra, và ghi mỗi dòng bắt đầu ở giây nào trong phim, thuộc đoạn `[Pnn]` nào. `qc` cộng mốc của dòng với mốc từng từ để có mốc tuyệt đối.
  - Câu: mỗi dòng của `lines.json` là một câu hoặc hơn; `qc` tách thêm theo dấu câu Whisper trả về; hết dòng là hết câu.
  - Mốc cảnh: lấy `cuts` trong `narration.json` nếu agent ghi (từ `timeline.json`); không có thì tìm từ hình bằng bộ lọc `scdet` của ffmpeg, ngưỡng 10 (edge case của spec).
- **Rationale**: phim cuối có cả nhạc, nên không tách được giọng từ âm thanh. Mốc từng từ đã có sẵn từ bước kiểm giọng của thư viện.
- **Kiểm chéo**: từ cuối cùng phải kết thúc trước hết phim, và tổng thời lượng các dòng phải khớp ±0,5 giây với `dur.json` của `tts.py`. Lệch thì báo lỗi "narration.json does not match the voice files".
- **Alternatives**: tách giọng khỏi nhạc bằng mô hình: nặng, không chính xác.

## R6. Model của biên tập (FR-007b)
- **Decision**: cài đặt `editor_model` có các giá trị `inherit` (mặc định), `opus`, `sonnet`, `haiku`. `inherit` lấy model của việc (`settings.model` online, hoặc model của phiên local).
  - Online: thêm vào Settings của admin như các cài đặt khác. Worker truyền `STUDIO_EDITOR_MODEL` vào container.
  - Local: `sh bin/studio config editor-model <giá trị>`, lưu ở `.studio/config.json`.
- **Rationale**: dùng bí danh model của Claude Code, nên không phải đổi khi có model mới.

## R7. Hình đứng im và chữ ô vuông (FR-012)
- **Hình đứng im**: bộ lọc `freezedetect=n=0.003:d=6` của ffmpeg trên phim cuối. Đây là "cài đặt QC của phong cách" của spec FR-012. Phong cách nào cho phép cảnh tĩnh dài hơn thì ghi trong `tools/filmcheck/styles.json` (`{"<slug>": {"still_max": 10}}`), của xưởng, không nằm trong `lib/`. Lúc đầu tệp rỗng. Phong cách riêng ghi `still_max` trong `my-styles/<slug>/qc.json`.
- **Chữ ô vuông**:
  1. `tools/filmcheck/texts.mjs` mở phim bằng `core/render/page.mjs` của thư viện (chỉ import, không sửa), giống readcheck, và gom chữ của `window.TEXTS(t)` mỗi 0,25 giây, cộng chữ của `<name>.srt`.
  2. Python lấy tập ký tự của các tệp phông trong thư mục phim bằng `fc-scan --format '%{charset}'`, và hỏi phông hệ thống bằng `fc-list ':charset=<mã>'`.
  3. Ký tự không phông nào có là lỗi.
  - Chromium trong container dùng phông hệ thống qua fontconfig, nên phép kiểm này khớp với lúc dựng.
  - Phim không có `window.TEXTS` thì chỉ kiểm `.srt`, và ghi "on-screen text not checked".
- **Kiểm khi implement**: `fc-scan` đọc được `.woff2` trong ảnh job. Không đọc được thì thêm `fonttools[woff]` vào venv.
- **Alternatives**: so ảnh chụp với ảnh có phông dự phòng: chậm, dễ sai với chữ động.

## R8. Cổng QC và thứ tự
- **Decision**: `worker.quality()` gọi `sh bin/studio qc <film> --json` trong container (như readcheck của 007) và gộp kết quả vào `qa`.
  - Các lỗi mới vào `qa.problems`, nên vòng sửa và trả lượt của 007 dùng y nguyên.
  - Thêm điều kiện: phim có lời đọc (có `narration.json` hoặc có `words.json` trong thư mục phim) thì `checks.json` PHẢI có `script.verdict = "pass"`. Không có thì đó là một lỗi QC.
  - Worker chạy lại `script check` để chắc kịch bản lúc giao vẫn đạt.
- **Biên tập hết 2 vòng mà chưa đạt** (FR-010): `script review` trả mã 3 và ghi `verdict = "failed"`.
  - Online: worker thấy `verdict = "failed"` thì `quotas.fail(…, "studio")` (trả lượt), không chờ agent.
  - Local: luồng làm phim dừng và báo người dùng.
- **Thứ tự bước**: `Treatment` → `Script` → (duyệt treatment nếu có, FR-019) → `Look` → `Voice` → … Tên bước `Script` thêm vào danh sách bước của `jobs` và `JOB.md`.
- **Duyệt treatment có kịch bản** (FR-019): `review request --kind treatment --film <name>` tự gắn `SCRIPT.md` và bảng điểm vào phần tóm tắt.

## R9. Giữ nguyên đoạn không bị ghi lỗi (FR-009)
- **Decision**: sau mỗi lượt biên tập, `script review` lưu bản kịch bản vào `films/<name>/.check/script-r<n>.md`. Ở lượt sau, `script check` so từng đoạn với bản trước.
  - Đoạn nào khác mà không bị ghi P1 hay P2 thì đó là lỗi cứng "P03 changed but was not flagged".
  - So sánh bỏ qua khoảng trắng ở cuối dòng.
- **Rationale**: kiểm bằng máy (SC-004), không dựa vào lời hứa của agent.

## R10. Kết quả chấm
- **Decision**: `films/<name>/checks.json` (máy đọc) và `films/<name>/CHECKS.md` (người đọc), cùng nội dung: các lượt chấm, số đo QC, kết luận ([contracts/files.md](contracts/files.md)).
  - Worker chép phần tóm tắt vào `job.qa` (`qa.script`, `qa.film`), để trang việc hiện được (FR-016).
  - Trang việc hiện bảng điểm và số đo trong khối "Quality" đang có của 007.
