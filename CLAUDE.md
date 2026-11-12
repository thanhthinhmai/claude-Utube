# CLAUDE.md

**claude-Utube** là một xưởng phim cho Claude. Xưởng xây bằng **Spec-Driven Development** của [GitHub Spec Kit](https://github.com/github/spec-kit).

## Các luồng làm việc
Mỗi yêu cầu đi đúng **một** luồng:

| Người dùng muốn | Luồng |
|---|---|
| Làm một bộ phim, video, clip (theo phong cách thư viện hoặc phong cách riêng) | **Làm phim** (bên dưới). Không tạo spec cho từng phim |
| Học phong cách của một kênh YouTube, danh sách video hoặc file video mẫu | **Học phong cách**: làm theo skill `.claude/skills/style-learn/SKILL.md`. Không tạo spec |
| Xây hoặc sửa skill, công cụ, cấu trúc của xưởng | **Spec-kit** (các mục bên dưới) |

### Chạy app trên máy (specs/014, nền cho app desktop)
- `sh bin/studio app start` chạy cả xưởng (giao diện, proxy, worker) trên máy này, không cần Docker, rồi in `URL: http://127.0.0.1:<cổng>`. Dữ liệu nằm ở `~/.local/share/claude-utube` (đổi bằng `--data`), không ghi vào thư mục dự án. Lần đầu mở: tạo chủ xưởng, rồi đăng nhập tài khoản Claude của chính người dùng ở AI accounts.
- `app status` · `app stop` (còn việc đang chạy thì từ chối, `--force` để dừng) · `app models` (tải mô hình Whisper) · `app import` (chép `films/`, `my-styles/`, `channels/` của dự án vào app).
- Khi app đang chạy, việc của luồng làm phim bằng chat (`job …`, `review …`) ghi vào sổ việc của app: xem và duyệt trên app; phim xong được chép (hard link) vào kho của chủ xưởng.

### App desktop (specs/015)
- `desktop/`: vỏ Electron (JavaScript thuần có `@ts-check`). Logic trong `desktop/core.js` (test: `node --test desktop/test/*.test.js`, đã nằm trong `tests/ui/run.sh`); cửa sổ, khay, thoát trong `desktop/main.js`. App chỉ gọi `sh bin/studio app …` của 014: macOS chạy thẳng, Windows chạy trong WSL2 (`wsl.exe -d <bản Linux> --cd <studio> -- sh bin/studio app …`).
- Chạy khi phát triển: `cd desktop && npm ci && npx electron .`. Terminal của VS Code đặt sẵn `ELECTRON_RUN_AS_NODE=1`, nên phải chạy `env -u ELECTRON_RUN_AS_NODE npx electron .`. Chạy thử không cần phần lõi thật: `CU_CONFIG_DIR=$(mktemp -d) CU_CORE_CMD='["node","test/fake-core.mjs"]' npx electron . --smoke`.
- GitHub Actions `.github/workflows/desktop.yml` chạy smoke trên Windows và macOS khi đẩy nhánh `NNN-desktop-*` hoặc bấm chạy tay (tốn phút chạy, macOS tốn gấp 10 lần).
- Bật WSL chỉ khi người dùng bấm "Turn on WSL" và đồng ý quyền quản trị (hiến pháp 2.2.0).

### Bộ cài (specs/016)
- Bộ cài chứa sẵn phần lõi: Windows là bản Linux `ClaudeUtube` (`deploy/core.Dockerfile`, `desktop/core-build/build-linux.sh`, cài bằng `wsl --import`); macOS là thư mục có Python, Node, FFmpeg riêng (`build-mac.sh`, giải nén vào `~/Library/Application Support/ClaudeUtube-core/<bản>`). Màn hình thiết lập cài phần lõi rồi tải mô hình (`fetch.sh voice`, `sh bin/studio app models`).
- Phát hành: gắn tag `desktop-vX.Y.Z` (hoặc bấm chạy tay `desktop-release`) → GitHub Release riêng tư có `.exe`, `.dmg`, `SHA256SUMS`. Mỗi lần chạy tốn khoảng 1 giờ phút chạy, phần lớn là macOS (tính gấp 10). Hướng dẫn cài cho người dùng: `desktop/INSTALL.md`.
- Phần lõi đóng gói có tệp `.core-version` (bỏ qua kiểm git của thư viện) và, trên macOS, `env.sh` (PATH tới Node, FFmpeg đi kèm). Thêm gói Python hay npm thì `desktop/core-build/credits-check.py` báo phải ghi vào `CREDITS`.
- Sandbox Bash của agent bật khi có `bwrap` và `socat` (bản Linux của app có sẵn) hoặc trên macOS (`STUDIO_AGENT_SANDBOX=1`).

### License và tự cập nhật (specs/017)
- Máy chủ license `tools/license/` (FastAPI, SQLite; triển khai bằng `deploy/license/`, xem README ở đó):
  - cấp key `CU-XXXX-…` (chỉ lưu mã băm), quản lý máy;
  - ký lease Ed25519 có hạn 7 ngày, app gia hạn mỗi khoảng 15 phút;
  - trang quản lý `/admin`, đăng nhập bằng mật khẩu đặt bằng `cli.py admin-password` trên VPS;
  - chuyển bản phát hành riêng tư cho app có lease còn tốt.
- App:
  - `desktop/license.js` (logic thuần) và `license.html`: hỏi key, khoá khi bị thu hồi hoặc hết hạn;
  - `desktop/updates.js`: kiểm `release.json` có chữ ký và SHA-256; Windows cài im lặng khi thoát, macOS mở `.dmg`.
- Phần lõi: `app start --gate <gate.json>`. `tools/studio/studio/gate.py` kiểm lease: khi cổng đóng, web trả 423 và worker không nhận việc mới.
- Bản build chỉ có license khi có biến repo `LICENSE_SERVER_URL` và khoá công khai trong `desktop/license-public-key.txt`. Khoá riêng chỉ nằm ở secret `LICENSE_SIGNING_KEY` và `.env` của VPS, **không bao giờ** vào repo hay vào chat.
- Test dùng khoá thử ở `desktop/test/vectors/` và máy chủ license giả `desktop/test/fake-license.mjs`.

### Chế độ Client (specs/018)
- Một bộ cài, hai chế độ: **Host** (chạy cả xưởng) hoặc **Client** (`mode: "client"`: chỉ cửa sổ app, không có phần lõi, không cần license).
- Host bật "Share with my team…" trên khay:
  - `desktop/share.js` mở cổng HTTPS (mặc định 47860) trước phần lõi; phần lõi vẫn chỉ nghe ở `127.0.0.1`;
  - chứng chỉ do `sh bin/studio app cert` tạo;
  - "Add a computer" cho mã ghép đôi dùng một lần, có hạn 10 phút.
- **Ghép đôi**: hai bên chứng minh cùng biết mã bằng HMAC gắn với dấu vân tay chứng chỉ, nên mã không đi qua mạng. Client lưu dấu vân tay, ghim nó (`setCertificateVerifyProc`) và gửi `X-CU-Client` trong mọi yêu cầu.
- **Cập nhật của Client** đi qua Host (`/__cu/update`, bằng lease của Host); Client kiểm chữ ký như 017.
- **Test**: `desktop/test/share.test.js`, Host giả `desktop/test/fake-host.mjs`, chứng chỉ thử ở `desktop/test/vectors/share-cert.json`.

### Luồng làm phim
1. Chạy `sh bin/studio status`. Nếu chưa sẵn sàng thì chạy `sh bin/studio setup` và báo người dùng công cụ còn thiếu (xưởng không tự cài phần mềm hệ thống).
2. Đọc `lib/lemo-opuscar/AGENTS.md` và làm theo, **ở chế độ skill** của thư viện, với các điểm thay thế sau:
   - `LIB` = đường dẫn tuyệt đối tới `lib/lemo-opuscar`. Chạy công cụ thư viện từ `$LIB`; `build.sh` ghi `LIB=<đường dẫn>` ở đầu, không dùng `../..`.
   - Thư mục phim = `films/<tên>/` của dự án (chữ thường, số, gạch nối). Nội dung `films/` không vào git.
   - Phong cách riêng: đọc danh mục `my-styles/README.md` và lưu vào `my-styles/<slug>/`, **thay cho** `~/lemo-my-styles/`.
   - Cài gói của thư viện bằng `sh bin/studio deps [voice] [music]`, **không** chạy thẳng `setup.sh` của thư viện (nó sẽ tải một bản thư viện khác vào `~/lemo-opuscar`).
   - **Dựng hình** (specs/019): ghi video bằng `sh bin/studio render <tên> --fps <rate của phong cách>` (bọc trong `job run … --step "Render"`), **không** gọi thẳng `video.mjs`; ảnh tĩnh, xuất sự kiện, kiểm thời gian đọc chữ bằng `sh bin/studio page still|events|readcheck <tên> …`. Xưởng tự dùng GPU nếu máy được (`sh bin/studio status` có dòng `dựng hình`), chia phim thành đoạn 10 giây, bị ngắt thì chạy lại để làm tiếp. Trên Linux/WSL2 có GPU, Chrome mở một cửa sổ ngoài màn hình: đừng tắt nó. Thiếu Chromium đầy đủ: `sh bin/studio deps gpu`; tắt GPU: `sh bin/studio config render software`.
2a. **Kênh** (specs/012): khi người dùng nói phim thuộc kênh nào (danh mục `channels/README.md`):
   - Ngay khi có tên phim: `sh bin/studio channel attach <tên> <kênh> --new [--style S] [--seconds N] [--language L] [--voice V]` (chỉ ghi giá trị người dùng nói riêng cho phim này). Rồi đọc `films/<tên>/CHANNEL_BRIEF.md` trước Treatment và làm theo: ngôn ngữ, độ dài, phong cách, luật tiêu đề và thumbnail, từ không dùng, bài học.
   - Mọi dòng của `lines.json` dùng `voice` và `speed` của kênh (`qc` kiểm). Hashtag bắt buộc của kênh vào `pack.json`.
   - Người dùng chốt điều mới cho kênh: `sh bin/studio channel decide <kênh> "<điều đã chốt>"`.
   - Tạo hoặc sửa kênh: `channel new|set|show` (xem `specs/012-channel-profile/contracts/cli.md`). Đây là kênh của chính người dùng; không ghi tên kênh tham chiếu.
   - **Bài học**: người dùng kể một lỗi ở phim đã giao → soạn nháp `sh bin/studio lesson draft <kênh|shared> --film <tên> --what "<lỗi gì>" --why "<vì sao lọt>" --stop "<cách chặn>" [--rule "phrase:<cụm từ>" | "max_sentence_words:N" | "max_title_chars:N"]`, in nháp ra và hỏi người dùng duyệt; duyệt thì `lesson approve <kênh|shared> <số>`. Lỗi đúng cho mọi kênh thì dùng `shared`. Không tự duyệt thay người dùng. Lỗi lặp lại một bài học là lỗi nặng: `script check` và `publish` báo `lesson_rule #n`.
2b. **Chọn đề** (specs/013), khi người dùng muốn tìm đề cho một kênh:
   - Cần khoá YouTube Data API: nhắc người dùng **tự chạy** `sh bin/studio config youtube-key` trong terminal của họ. Không bao giờ nhận khoá qua chat, không in khoá.
   - `sh bin/studio topics score <kênh> "<đề 1>" "<đề 2>" … [--suggest]` (tối đa 20 đề; `--suggest` để xưởng gợi ý thêm tối đa 10 đề). Đọc bảng điểm (5 mục /10, GO, HOLD, DROP, PRIORITY, video bằng chứng) và tóm tắt cho người dùng.
   - Phim kế tiếp: `topics take <kênh> --film <tên>` lấy đề đầu hàng đợi (bỏ qua đề cùng kiểu với 2 phim gần nhất, đề kênh mẫu vừa đăng, đề cũ quá 14 ngày), rồi `channel attach <tên> <kênh> --new --topic <số>`. `publish` đạt thì đề tự chuyển sang "đã làm".
   - Kênh mẫu: `topics refs <kênh> --add UC…`. Kết quả, kênh mẫu và bằng chứng nằm trong `channels/<kênh>/topics.json`, `TOPICS.md`, `references.json` (không vào git; không nêu tên kênh nào trong phim).
3. **Kịch bản được chấm** (specs/010, phim có lời đọc), xen vào quy trình của thư viện:
   - Sau bước Brief: ghi `films/<tên>/BRIEF.md` (tóm tắt yêu cầu, tối đa 2000 ký tự).
   - Sau `TREATMENT.md`, trước giọng đọc: viết `SCRIPT.md` và `SOURCES.md` theo `specs/010-script-review-qc/contracts/files.md`. Tìm số liệu bằng WebSearch (tối đa 5 lượt); mở mọi đường dẫn được dẫn bằng `sh bin/studio web fetch <url> --film <tên>`.
   - `sh bin/studio script check <tên>` tới khi đạt, rồi `sh bin/studio script review <tên>`. Mã 1: chỉ sửa các đoạn bị ghi P1 hoặc P2, rồi chạy lại. Mã 3 (hết 2 vòng sửa): dừng, báo người dùng điểm cuối và các lỗi còn lại.
   - Phim không có lời đọc: `sh bin/studio script skip <tên> --reason "no narration"`.
   - Lời của `lines.json` lấy đúng từ kịch bản đã đạt (`qc` kiểm); xong giọng thì ghi `narration.json` có `lines_file`.
   - Ở bước Self-check: `sh bin/studio qc <tên>` (nhịp lời, cắt cảnh, hình đứng im quá 6 giây, ký tự thiếu phông). Sửa một vòng theo lỗi nó báo; còn lỗi thì báo người dùng một dòng khi giao.
3a. **Gói đăng** (specs/011, mọi phim), sau Self-check:
   - Viết `films/<tên>/publish/pack.json` theo `specs/011-publish-pack/contracts/files.md`: 3 tiêu đề (tò mò, con số hoặc lợi ích, câu hỏi), mỗi tiêu đề có một thumbnail (thời điểm lấy từ bảng ảnh Self-check, chữ trên ảnh bổ sung chứ không lặp tiêu đề), 2 dòng mở đầu, tóm tắt, chương, 3–5 hashtag. Viết bằng ngôn ngữ của phim; số chỉ lấy từ `SCRIPT.md` hoặc `SOURCES.md`; không nêu tên kênh nào.
   - `sh bin/studio publish <tên>`. Mã 1: sửa `pack.json` một lần rồi chạy lại; còn lỗi thì báo người dùng một dòng khi giao. Gói đăng không chặn việc giao phim.
   - Phim cũ đã xong (kể cả trước 010): người dùng nhờ "làm gói đăng cho <tên>" thì làm đúng hai bước trên, không dựng lại phim.
4. Không sửa file nào trong `lib/` (hiến pháp VI). Muốn dùng phiên bản thư viện mới thì đổi `library.lock` theo quy trình spec-kit.
5. **Ghi việc lên giao diện** (`specs/003-studio-ui/contracts/skill-integration.md`):
   - Khi đã có tên phim: `sh bin/studio job start --kind film --name <tên> --film <tên>`; lưu dòng đầu (mã việc) vào `films/<tên>/.job`; in dòng `URL: …` cho người dùng ("Theo dõi trên giao diện: <URL>").
   - Đầu mỗi giai đoạn: `sh bin/studio job step <mã> "<giai đoạn>"`, ghi đúng một trong các tên tiếng Anh: `Treatment`, `Script`, `Look`, `Storyboard`, `Voice`, `Music`, `Picture`, `Mix`, `Render`, `Self-check`, `Publish`.
   - Lệnh dài (render, mux, tạo giọng): bọc bằng `sh bin/studio job run <mã> --step "<giai đoạn>" -- <lệnh…>` (cùng danh sách tên trên).
   - Xong: `sh bin/studio job done <mã> --film <tên>`; lỗi không tự sửa được: `sh bin/studio job fail <mã> "<lỗi>"`.
   - Storyboard (nếu người dùng yêu cầu) vẫn duyệt trong khung chat.
   - `job start` báo chưa cài giao diện (mã 1): bỏ qua các lệnh `job`, làm phim như cũ, gợi ý một lần `sh bin/studio deps ui`.

## Luật bắt buộc
- Đọc `.specify/memory/constitution.md` trước khi lập kế hoạch hoặc viết code. Hiến pháp có hiệu lực cao nhất.
- Trước khi làm, **chọn mức quy trình** theo bảng dưới và báo cho người dùng một dòng, ví dụ: "Mức: Nhẹ, vì chỉ sửa 2 file". Người dùng có thể yêu cầu đổi mức.
- Ở mức Nhẹ và Đầy đủ: không viết code khi spec và plan chưa được người dùng duyệt.
- Chạy từng lệnh một. Sau mỗi lệnh, dừng lại tóm tắt kết quả và chờ người dùng duyệt.
- Chỗ nào chưa rõ thì hỏi, không đoán.

## Chọn mức quy trình (để tiết kiệm token)

| Mức | Khi nào | Các bước |
|---|---|---|
| **Trực tiếp** | Sửa bug nhỏ đã rõ nguyên nhân, đổi chữ hoặc CSS, đổi cấu hình; ≤ 1–2 file và không đổi hành vi chính | Sửa luôn, chạy test hoặc chạy thử, báo kết quả. Không tạo spec |
| **Nhẹ** | Tính năng nhỏ, ~1–5 file, yêu cầu đã rõ, không đổi dữ liệu hay API dùng chung | `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement` |
| **Đầy đủ** | Tính năng hoặc ứng dụng mới, game hoặc module mới, đổi dữ liệu hoặc API, yêu cầu còn mơ hồ, hoặc người dùng yêu cầu | Cả 7 bước ở bảng dưới |

Quy tắc nâng mức:
- Đang ở mức Trực tiếp mà thấy cần sửa hơn 2 file hoặc đổi hành vi chính → dừng lại, đề xuất chuyển sang mức Nhẹ.
- Đang ở mức Nhẹ mà spec còn từ 2 chỗ `[NEEDS CLARIFICATION]` trở lên, hoặc tasks vượt khoảng 15 việc → đề xuất chuyển sang mức Đầy đủ.
- Đang không chắc giữa hai mức → chọn mức cao hơn.

Ở mức Nhẹ:
- Spec chỉ cần user story P1, yêu cầu chính và tiêu chí thành công đo được.
- Bỏ qua `research.md` và `contracts/` nếu không cần.
- Sau khi implement, tự đối chiếu nhanh với tiêu chí thành công thay cho `/speckit-converge`.

Mẹo chung để tiết kiệm token:
- Chỉ dùng `/speckit-checklist` khi người dùng yêu cầu.
- Mỗi tính năng nên làm trong một phiên mới.
- Đọc tài liệu theo từng phần cần thiết, không đọc lại cả file khi không cần.

## Quy trình đầy đủ
| Bước | Lệnh | Kết quả |
|---|---|---|
| 1 | `/speckit-specify <mô tả>` | `specs/NNN-x/spec.md` + nhánh mới |
| 2 | `/speckit-clarify` | Câu hỏi làm rõ, câu trả lời được ghi vào spec |
| 3 | `/speckit-plan <công nghệ>` | `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` |
| 4 | `/speckit-tasks` | `tasks.md` |
| 5 | `/speckit-analyze` | Báo cáo mâu thuẫn (chỉ đọc) |
| 6 | `/speckit-implement` | Code |
| 7 | `/speckit-converge` | Thêm task cho phần còn thiếu. Lặp lại 6–7 đến khi `Converged` |

Lệnh phụ: `/speckit-checklist <lĩnh vực>` tạo checklist kiểm tra chất lượng spec (UX, bảo mật…). `/speckit-constitution` dùng để sửa hiến pháp.

## Cấu trúc
- `bin/studio`: `setup` · `status [--json]` · `render <phim>` · `page still|events|readcheck <phim>` · `deps gpu` · `config render auto|software` · `deps [voice] [music]` · `deps learn [--extra]` · `learn <lệnh>` · `deps ui` · `ui [open|status|stop]` · `job …` · `review …` · `deps online` · `admin create <email>` · `online up|down|logs|admin <email>` · `script check|review|status|skip <phim>` · `web fetch <url>` · `app start|status|stop|import` · `qc <phim>` · `publish <phim>` · `channel …` · `lesson …` · `topics …` · `config youtube-key` · `config editor-model …`; test: `sh tests/run.sh`, `sh tests/render/run.sh`, `sh tests/learn/run.sh`, `sh tests/ui/run.sh`, `sh tests/filmcheck/run.sh`, `sh tests/online/run.sh`, `sh tests/license/run.sh` (bài chạy thật, tốn tiền: `sh tests/online/live.sh`)
- `tools/studio/`: giao diện web và API v1 (chỉ `127.0.0.1`), sổ việc và yêu cầu duyệt trong `.studio/` (không vào git)
- Chế độ online (specs/007, specs/008, `STUDIO_MODE=online`): xưởng nội bộ chạy bằng gói Claude Pro/Max của chủ xưởng. Tài khoản, hạn mức, việc và từng lần gọi Claude nằm trong SQLite ở `$STUDIO_DATA`; đăng nhập các tài khoản Claude nằm ở `$STUDIO_DATA/claude/slot-<n>` (quyền 700, không vào git, không vào container). `tools/studio/studio/claude_plan.py`: đăng nhập, làm mới mã, chọn tài khoản. Không có đăng ký công khai: chủ xưởng thêm người trong Settings → Users. `tools/runner/` gồm `worker.py` (hàng đợi, chạy mỗi việc trong một container), `proxy.py` (đổi mã của việc sang tài khoản Claude dùng ít nhất, khoá API chỉ là dự phòng, ghi token) và `agent.py` (Claude Agent SDK trong container). Mã API (specs/009): `tools/studio/studio/tokens.py` (mã, nhật ký, vé dùng một lần, Idempotency-Key); mỗi người tự tạo mã ở Your account, Owner xem và thu hồi ở Settings → API tokens; Settings → Worker xem worker và việc gần nhất. Máy chủ MCP ở `/api/mcp` (`tools/studio/studio/mcp_server.py`, chỉ nhận mã): mỗi công cụ là một lệnh REST với cùng mã. `deploy/` chứa Dockerfile, `compose.yaml`, Caddyfile và hướng dẫn `deploy/README.md`
- `tools/filmcheck/` (specs/010, 011): gói đăng (`publish.py`, thumbnail vẽ từ trang của phim bằng `thumbs.mjs`), kênh và bài học (`channels.py`, specs/012), chọn đề (`topics.py`, `topics_fit.py`, specs/013), máy chấm kịch bản (`script.py`), biên tập độc lập (`editor.py`, một `claude -p` riêng), mở trang an toàn (`webfetch.py`, online đi qua bộ chuyển tiếp), đo phim (`qc.py`), kết quả `checks.json` và `CHECKS.md` trong thư mục phim (`report.py`). Chỉ cần Python 3
- `tools/render/` (specs/019): `probe.mjs` (GPU hay phần mềm), `record.mjs` (ghi video theo đoạn, làm tiếp được), `chrome-gpu.sh` (bọc Chromium đầy đủ cho biến `PLAYWRIGHT_CHROME` của thư viện); test: `sh tests/render/run.sh`
- `tools/style-learn/`: công cụ đo và lưu phong cách (venv riêng `tools/.venv`, không vào git); skill `.claude/skills/style-learn/`
- `library.lock`: phiên bản thư viện đã ghim; `lib/lemo-opuscar/`: thư viện (không vào git, không sửa)
- `channels/`: hồ sơ kênh của chính xưởng và bài học (vào git, specs/012) · `my-styles/`: phong cách riêng (vào git) · `films/`: phim (không vào git) · `references/`: video tham chiếu (không vào git) · `tools/`: công cụ tự viết
- `desktop/`: app desktop (Electron, specs/015) · `CREDITS`: giấy phép của phần mềm bên thứ ba
- `.specify/memory/constitution.md`: hiến pháp
- `.specify/templates/`: mẫu cho spec, plan, tasks, checklist
- `.specify/scripts/bash/`: script tạo nhánh và thư mục tính năng
- `.claude/skills/speckit-*/`: các lệnh `/speckit-*`
- `specs/NNN-ten-tinh-nang/`: tài liệu của từng tính năng
