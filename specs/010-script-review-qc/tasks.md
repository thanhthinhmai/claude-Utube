# Tasks: Kịch bản được chấm và QC video tự động

**Input**: `specs/010-script-review-qc/` (spec.md, plan.md, research.md, data-model.md, contracts/cli.md, contracts/files.md, quickstart.md). Nền là 007 (cổng QC, việc online) và 008 (chế độ gói, `fake_claude`, `claude -p`).

**Tests**: có. Spec đòi test tự động cho SC-001 … SC-004 và SC-006. Test không cần mạng và không tốn hạn mức:
- kịch bản mẫu và phim mẫu tạo bằng ffmpeg ngay trong test;
- biên tập giả qua `STUDIO_CLAUDE_BIN`;
- proxy giả cho `web fetch`.

**Luật chung cho mọi task**:
- Không sửa `lib/` (hiến pháp VI). Không commit media; phim mẫu chỉ tạo trong `tests/filmcheck/.tmp/` (bỏ qua bởi git).
- Máy chấm và `qc` không gọi Claude, không cần mạng.
- Chữ in ra màn hình bằng tiếng Anh, ngắn (giống 005).
- Sau mỗi phase, 5 bộ test phải đạt: `tests/run.sh`, `tests/learn/run.sh`, `tests/ui/run.sh`, `tests/online/run.sh`, `tests/filmcheck/run.sh`.
- Commit sau mỗi phase (hiến pháp, quy trình 4).

## Phase 1: Setup

- [X] T001 Kiểm 3 mục "Kiểm khi implement" của research.md và ghi vào mục mới "Kết quả kiểm T001" ở cuối `specs/010-script-review-qc/research.md`:
  - R3: trong ảnh `studio-job`, khi một phiên Agent SDK đang chạy, `claude -p` thứ hai với cùng `CLAUDE_CODE_OAUTH_TOKEN` và `ANTHROPIC_BASE_URL` chạy xong và trả JSON theo `--json-schema`. Thử bằng proxy giả của `tests/online/helpers.py`, không cần tài khoản thật;
  - R4: `WebSearch` của Claude Code đi qua proxy ở chế độ gói (một tài khoản thật trên máy này, một câu hỏi), và `usage.server_tool_use.web_search_requests` có trong phản hồi;
  - R7: `fc-scan --format '%{charset}'` đọc được một tệp `.woff2` trong ảnh `studio-job`.
  - **Nếu một mục khác research thì dừng ở đây và hỏi người dùng** (hiến pháp II).
- [X] T002 [P] Tạo khung `tools/filmcheck/`:
  - `cli.py` với argparse và các lệnh con rỗng: `script check|review|status|skip`, `web fetch`, `qc`, `config editor-model`;
  - `__init__.py`.

  Trong `bin/studio`, thêm `script | web | qc | config` vào `case`; chạy `tools/filmcheck/cli.py` bằng `$VENV/bin/python` nếu có, không thì `python3`; không cần giao diện. Thêm các lệnh này vào `usage`.
- [X] T003 [P] Tạo `tests/filmcheck/run.sh` (giống `tests/learn/run.sh`, `unittest discover`) và `tests/filmcheck/samples.py`:
  - kịch bản mẫu tốt (en và vi) và các kịch bản lỗi, mỗi kịch bản một luật của contracts/cli.md;
  - hàm `make_film(path, spec)` tạo phim mẫu bằng ffmpeg: `testsrc2` có cắt cảnh ở mốc cho trước, đoạn đứng im, tiếng `sine`, kèm `narration.json` và `words.json` giả.

  Thêm `tests/filmcheck/.tmp/` vào `.gitignore`.

---

## Phase 2: Foundational (chặn mọi user story)

- [X] T004 Viết `tools/filmcheck/report.py`: đọc và ghi `films/<name>/checks.json` đúng lược đồ ở contracts/files.md (ghi nguyên tử, giữ các phần đã có), và sinh `CHECKS.md` (bảng điểm từng lượt, danh sách lỗi, bảng số đo kèm ngưỡng, kết luận). Test trong `tests/filmcheck/test_report.py`.
- [X] T005 [P] Viết `tools/filmcheck/webfetch.py` theo research R4:
  - `fetch(url) -> {status, final_url, content_type, text}`;
  - chỉ `http`/`https`, cổng 80/443;
  - phân giải tên, từ chối địa chỉ riêng, loopback, link-local, đa hướng, `0.0.0.0/8`, `100.64.0.0/10`, IPv6 ULA; kiểm lại ở mỗi lần chuyển hướng (tối đa 3);
  - tối đa 2 MB, 15 giây; chỉ nhận `text/html`, `text/plain`, `application/json`, `application/xml`;
  - bỏ thẻ HTML, `script` và `style`, gộp khoảng trắng, cắt ở 20 000 ký tự.

  Lỗi trả theo mã ở contracts/cli.md (`blocked_address`, `too_large`, `unsupported_type`, `timeout`). Test trong `tests/filmcheck/test_webfetch.py` bằng máy chủ HTTP cục bộ cho phần rút chữ, và bằng hàm phân giải giả cho phần chặn địa chỉ.
- [X] T006 [P] Cài đặt model của biên tập (research R6):
  - online: thêm `editor_model` vào `tools/studio/studio/db.py` (mặc định `"inherit"`) và `quotas.py` (`RANGES`: một trong `inherit`, `opus`, `sonnet`, `haiku`);
  - local: `config editor-model` trong `tools/filmcheck/cli.py` ghi `.studio/config.json`;
  - hàm `editor_model()` trong `tools/filmcheck/editor.py`: `STUDIO_EDITOR_MODEL` nếu có, không thì `.studio/config.json`, không thì `inherit`. `inherit` nghĩa là không truyền `--model` (Claude Code dùng model của phiên) hoặc truyền `STUDIO_MODEL` khi có.

  Test giá trị sai bị từ chối (`422` online, mã 2 local).
- [X] T007 [P] Mở rộng `tests/online/fake_claude`: khi `-p` có `--json-schema` chứa `"checked_sources"` thì trả lời như biên tập, và ghi các tham số đã nhận vào `$FAKE_CLAUDE_LOG`. Điều khiển bằng thẻ trong `SCRIPT.md`:
  - `[editor-pass]` (mặc định): score 9, không lỗi;
  - `[editor-p1 Pnn]`: score 8, một P1 ở `Pnn` cho tới khi đoạn đó đổi;
  - `[editor-low]`: score 6 mọi lượt;
  - `[editor-bad-json]`: trả sai lược đồ.

**Checkpoint**: khung lệnh chạy được; `webfetch` và `report` có test; 5 bộ test đạt. Commit.

---

## Phase 3: User Story 1 - Lời đọc được chấm trước khi thu giọng (P1) 🎯 MVP

**Goal**: phim có lời đọc có `SCRIPT.md` và `SOURCES.md` qua máy chấm (≥ 7) và biên tập (≥ 8, không P1) trước file giọng đầu tiên; hết 2 vòng mà chưa đạt thì dừng (online trả lượt).

**Independent Test**: spec US1. Tự động thì dùng việc giả online với `fake_agent.py` và `fake_claude`; bằng tay thì làm theo quickstart bước 1.

- [X] T008 [US1] Viết phần đọc tệp trong `tools/filmcheck/script.py` theo contracts/files.md và data-model:
  - phần đầu: `Title` (bắt buộc, "≤ 100 ký tự"), `Target` ("số nguyên 5–900" giây, hậu tố `s`), `Language`, `Speed` (tuỳ chọn);
  - đoạn `[Pnn]` "tăng dần từ `P01`, không trùng; nội dung không rỗng"; dòng `>` bỏ qua;
  - `SOURCES.md`: mỗi dòng `- [Pnn] "<trích>": <tên>, <năm>, <đường dẫn>` (năm 4 chữ số; `para` có trong kịch bản; `quote` có trong đoạn đó, không phân biệt hoa thường), hoặc đúng một dòng `no factual claims`;
  - tách câu, đếm từ hay ký tự theo ngôn ngữ (research R2).
- [X] T009 [US1] Viết máy chấm trong `script.py` (`check(film_dir) -> result`):
  - điều kiện cứng `format`, `sources` (câu có con số cần nguồn: chữ số, hoặc số viết bằng chữ từ mười/ten trở lên theo spec FR-004; đường dẫn phải có trong `.check/opened.json` với mã 2xx, hoặc `provided:`), `length` (±15% `Target` theo tốc độ đọc);
  - bảng trừ điểm ở contracts/cli.md: `long_sentence`, `no_hook`, `intro_opening`, `retention_gap`, `cliche`, `risky_number`, `punctuation`, kèm vị trí `Pnn.câu`;
  - tạo `tools/filmcheck/cliches/en.txt` và `vi.txt` (khoảng 40 cụm mỗi tệp), cùng danh sách dấu hiệu hook và câu mở đầu cấm theo ngôn ngữ trong `script.py`.
- [X] T010 [US1] Viết so đoạn (research R9) trong `script.py`: có `.check/script-r<n>.md` thì so từng đoạn với bản mới nhất. Đoạn khác mà lượt biên tập trước không ghi P1/P2 cho nó là lỗi cứng `unchanged`; so sánh bỏ khoảng trắng cuối dòng.
- [X] T011 [US1] Viết `tests/filmcheck/test_script.py`:
  - mỗi kịch bản mẫu lỗi trượt đúng luật của nó và đúng vị trí; kịch bản tốt đạt ≥ 7;
  - edge case phim < 30 giây (cửa sổ hook 20%, không đòi điểm giữ chân);
  - tiếng Trung đếm ký tự (40);
  - `no factual claims`;
  - so đoạn (SC-004);
  - SC-002: kịch bản 300 giây chấm xong < 5 giây và không mở tiến trình con nào (`subprocess` bị chặn trong test).
- [X] T012 [US1] Viết `tools/filmcheck/editor.py` (research R3, contracts/cli.md):
  - chạy `claude_bin()` (dùng lại `studio.claude_plan.claude_bin` nếu import được, không thì `STUDIO_CLAUDE_BIN` hoặc `claude` trên PATH) với `-p`, lời nhắc cố định, `--json-schema` biên tập, `--output-format json`, `--no-session-persistence`, `--tools "Read,Grep,WebSearch,Bash"` (giới hạn danh sách) cùng `--allowedTools "Read Grep WebSearch Bash(sh bin/studio web fetch:*)"` (cho phép chạy; kết quả T001), và `--model` theo T006; đặt `XDG_CACHE_HOME=/tmp`;
  - lời nhắc chỉ đưa đường dẫn `SCRIPT.md`, `SOURCES.md`, `TREATMENT.md` và yêu cầu của phim (`/work/.input.json` online, `films/<name>/BRIEF.md` local nếu có);
  - lời nhắc yêu cầu: mở lại nguồn của các con số chính bằng `web fetch` và ghi P1 cho số không khớp (FR-007a); tìm web tối đa 3 lượt (mỗi lượt khoảng 14 000 token, T001); lỗi gắn số đoạn có thật; điểm ≥ 8 chỉ khi không còn P1;
  - sai lược đồ thì chạy lại một lần; vẫn sai thì tính là một lượt không đạt (thoát 1, hoặc 3 ở lượt cuối; contracts/cli.md).
- [X] T013 [US1] Viết `script check|review|status|skip` trong `tools/filmcheck/cli.py` đúng mã thoát ở contracts/cli.md:
  - `review` từ chối khi `check` chưa đạt; lưu `.check/script-r<n>.md` và `review-r<n>.json`; tính vòng: lượt 1 cộng tối đa 2 vòng sửa; hết thì `verdict = failed`, mã 3;
  - `skip` chỉ khi không có `voices/` và `narration.json`;
  - mọi lệnh ghi `checks.json` và `CHECKS.md` qua `report.py`;
  - in lỗi dạng `P02.1 long_sentence 31 words`.
- [X] T014 [US1] Viết `web fetch` trong `cli.py`:
  - local thì gọi `webfetch.fetch`;
  - online (`STUDIO_MODE=online` và `STUDIO_JOB`) thì `POST {STUDIO_PROXY}/internal/web/fetch` với mã của việc (cùng cách `studio_cli.proxy_call`);
  - `--film` ghi `.check/opened.json`.

  Trong `tools/runner/proxy.py`, thêm `POST /internal/web/fetch`:
  - xác thực mã của việc như `/internal/jobs/*`;
  - gọi `webfetch.fetch` trong luồng phụ;
  - đếm tối đa 60 trang mỗi việc (`429 fetch_limit`);
  - nhật ký chỉ ghi tên miền và mã.
- [X] T015 [US1] Sửa `tools/runner/proxy.py`: đọc `usage.server_tool_use.web_search_requests`, cộng vào hàng Call và vào chi phí khi `via = api` (10 USD cho 1000 lượt, thêm vào `price_table`).
  - Đã làm: số lượt cộng vào `job.web_searches` (không thêm cột cho bảng Call, nên không đổi lược đồ); chi phí qua `quotas.WEB_SEARCH_USD` = 0,01 USD mỗi lượt khi `via = api`.
- [X] T016 [US1] Sửa `tools/runner/agent.py`:
  - bỏ `WebSearch` khỏi `disallowed_tools` và thêm vào `allowed_tools` (giữ cấm `WebFetch`);
  - `rules()` nói: mở trang bằng `sh bin/studio web fetch <url> --film <name>`.

  Sửa `tools/runner/worker.py`: truyền `STUDIO_EDITOR_MODEL` (từ cài đặt; `inherit` thì không truyền) vào container và vào `LocalRunner`.
- [X] T017 [US1] Sửa `tools/runner/JOB.md` và mục "Luồng làm phim" của `CLAUDE.md`:
  - local: sau bước Brief, ghi `films/<name>/BRIEF.md` theo contracts/files.md;
  - thêm bước `Script` sau `Treatment`: viết `SCRIPT.md` và `SOURCES.md` theo contracts/files.md (tìm bằng WebSearch, tối đa 5 lượt theo T001; mở bằng `web fetch --film`);
  - `script check` tới khi đạt, rồi `script review`; mã 1 thì chỉ sửa đúng các đoạn bị ghi; mã 3 thì dừng (online: `job fail --by studio` với điểm cuối; local: báo người dùng);
  - phim không lời thì `script skip`;
  - lời đọc của `lines.json` lấy đúng từ kịch bản đã đạt.

  Thêm `Script` vào danh sách tên bước (JOB.md, CLAUDE.md mục 4, `specs/003-studio-ui/contracts/skill-integration.md`) và vào nơi giao diện liệt kê bước nếu có.
- [X] T018 [US1] Sửa `tools/runner/worker.py`, phần nhận kết quả của agent:
  - `checks.json.script.verdict == "failed"` thì `self.failed(job, "The script did not pass review after 2 rounds: …", "studio")` (trả lượt);
  - phim có lời đọc (`narration.json` hoặc `words.json` trong thư mục phim) mà verdict khác `pass` thì đó là một lỗi trong `qa.problems`;
  - worker chạy lại `script check` trong container trước khi chấp nhận.
- [X] T019 [US1] FR-019:
  - `review request --kind treatment --film <name>` (trong `tools/studio/studio_cli.py`, cả `remote_review`) gắn nội dung `SCRIPT.md` và bảng điểm vào sau phần tóm tắt khi có kịch bản;
  - `JOB.md` và lời nhắc của `agent.py` khi `review_treatment`: gửi duyệt sau khi kịch bản đạt;
  - việc tiếp tục sau khi người giao phim yêu cầu sửa (`resume_answered`): lời nhắc nói phải qua lại `script check` và `script review`, và vòng này không tính vào giới hạn (`cli.py` nhận `--customer-round`).
- [X] T020 [US1] Mở rộng `tests/online/fake_agent.py` cho bước Script (thẻ `[narration]`: viết `SCRIPT.md`, `SOURCES.md`, chạy `script check` và `script review` thật với `fake_claude`, sửa đoạn bị ghi, rồi làm phim giả có `narration.json`). Viết `tests/online/test_script_step.py`:
  - việc đạt sau 1 vòng sửa: `checks.json` có 2 lượt biên tập, `fix_rounds = 1`, mốc của lượt đạt trước file giọng giả (SC-001);
  - `[editor-low]`: việc lỗi do xưởng, lượt được trả, không có `voices/`;
  - `[editor-bad-json]` hai lần: tính một lượt không đạt (mã 1);
  - FR-016: các lần gọi của biên tập có hàng Call gắn với việc, và `job.tokens` gồm cả phần đó;
  - duyệt treatment có kịch bản (FR-019): phần tóm tắt của review chứa `[P01]` và điểm;
  - `fake_claude` nhận `--model sonnet` khi cài đặt là `sonnet`, và không nhận `--model` khi `inherit`;
  - `test_web_fetch.py`: proxy chặn `http://proxy:8780`, `http://127.0.0.1` và `http://10.0.0.1`; đếm tới 60; nhật ký không có đường dẫn đầy đủ.

**Checkpoint**: MVP. Kịch bản được chấm và chặn trước khi thu giọng, cả local và online. Commit.

---

## Phase 4: User Story 2 - Máy QC đo nhịp lời và hình (P2)

**Goal**: `qc` đo 7 mục của contracts/cli.md; worker gộp vào cổng QC của 007 với một vòng sửa.

**Independent Test**: spec US2, bằng phim mẫu tạo bằng ffmpeg.

- [ ] T021 [US2] Viết phần lời đọc của `tools/filmcheck/qc.py` (research R5):
  - đọc `narration.json`, `words.json`, `dur.json`; mốc tuyệt đối = `at` + mốc từ;
  - kiểm chéo: tổng thời lượng khớp `dur.json` ±0,5 giây, từ cuối trước hết phim;
  - đo `silence_ratio` (≤ 0,20), `long_pause` (≥ 0,8 giây chỉ giữa hai đoạn khác nhau), `tail` (≤ 1,5 giây);
  - câu: hết dòng là hết câu, tách thêm theo `.?!` trong chữ Whisper.
- [ ] T022 [US2] Viết phần hình của `qc.py`:
  - mốc cảnh từ `cuts`, không có thì `ffmpeg … -vf "scdet=threshold=10"`;
  - `cut_in_sentence` (không cắt trong câu; cắt ≥ min(0,4 giây, khoảng nghỉ) sau từ cuối của câu trước);
  - `key_shot` (cảnh có từ cuối của mỗi đoạn ≥ 2,5 giây);
  - `still` bằng `freezedetect=n=0.003:d=<still_max>`, với `still_max` = 6 hoặc giá trị trong `tools/filmcheck/styles.json` (tạo `{}`) hay `my-styles/<slug>/qc.json`. Slug đọc từ `TREATMENT.md` dòng `Style:` hoặc từ `.input.json`.
- [ ] T023 [US2] Viết `tools/filmcheck/texts.mjs` (mở phim bằng `$LIB/core/render/page.mjs`, gom chữ của `window.TEXTS(t)` mỗi 0,25 giây, in JSON; không có `TEXTS` thì in `{"texts": null}`) và phần phông trong `qc.py`:
  - ký tự của TEXTS và `<name>.srt`;
  - tập ký tự của phông trong thư mục phim bằng `fc-scan --format '%{charset}'`;
  - ký tự chưa có thì hỏi `fc-list ':charset=<hex>' file` (gộp một lần cho mọi ký tự, có cache);
  - bỏ qua khoảng trắng và ký tự điều khiển; ghi `missing_glyphs` và `texts_checked`.
- [ ] T024 [US2] Viết `qc` trong `cli.py`: chạy các phần trên, ghi `film` vào `checks.json` và `CHECKS.md`, in từng lỗi kèm mốc giây, mã 0/1/2. Phim không lời chỉ đo `still` và `missing_glyph`.
- [ ] T025 [US2] Viết `tests/filmcheck/test_qc.py` (SC-003, SC-006):
  - một phim mẫu đạt (0 lỗi);
  - các phim mẫu lỗi, mỗi phim trượt đúng một mục với mốc đúng ±0,1 giây: lặng 30%, lặng 1,2 giây giữa đoạn, cắt giữa câu, cảnh chốt 1,5 giây, đuôi 3 giây, đứng im 8 giây;
  - ký tự thiếu phông: một `.srt` có ký tự riêng (U+E000), chỉ chạy khi có `fc-list`;
  - `narration.json` lệch `dur.json` thì mã 2;
  - `qc` cho phim 60 giây xong < 60 giây.
- [ ] T026 [US2] Sửa `tools/runner/worker.py` `quality()`: chạy `sh bin/studio qc <film> --json` trong container qua `runner.exec`; mã 1 thì thêm các lỗi vào `qa.problems` (vòng sửa và trả lượt như 007); mã 2 thì ghi `qa.film = "not_checked"` và một lỗi "the film could not be measured: …".

  Sửa `JOB.md` và `CLAUDE.md`: ghi `narration.json` khi dựng lời (từ `timeline.json` và `words.json`); chạy `qc` ở bước `Self-check` trước `job done`.
- [ ] T027 [US2] Sửa `tests/online/fake_agent.py` (thẻ `[qc-bad]`: phim có đuôi 3 giây ở lần đầu, sửa ở lần resume) và thêm vào `tests/online/test_script_step.py`:
  - lần đầu trượt `tail`, resume với số đo, lần hai đạt;
  - `[qc-bad-always]`: việc lỗi do xưởng, lượt được trả.

**Checkpoint**: commit.

---

## Phase 5: User Story 3 - Theo dõi kết quả chấm (P3)

**Goal**: trang việc và thư mục phim hiện điểm, số vòng và số đo.

**Independent Test**: spec US3.

- [ ] T028 [US3] Sửa `tools/runner/worker.py`: sau QC, chép tóm tắt `checks.json` vào `job.qa.script` (`{verdict, machine_score, editor_score, fix_rounds, p1, p2, p3, model}`) và `job.qa.film` (data-model "QC result"). Sửa `api_online.py` `view()` để trả các trường này cho người giao việc và admin.
- [ ] T029 [US3] Sửa `tools/studio/studio/web/app.js` và `style.css` (giữ `@ts-check`, 0 lỗi):
  - khối "Quality" của trang việc hiện điểm máy chấm và điểm biên tập từng lượt, số lỗi P1/P2/P3, số vòng sửa, model, và bảng số đo QC với ngưỡng và đạt/trượt;
  - Settings → General có ô chọn "Script editor model" (`inherit` hiện là "Same as jobs").

  Mọi chữ tiếng Anh.
- [ ] T030 [US3] Viết `tests/online/test_quality_view.py` (API: `qa.script` và `qa.film` sau một việc giả có 1 vòng sửa) và mở rộng `tests/online/browser_admin.cjs` hoặc một tệp `browser_quality.cjs` mới (trang việc hiện điểm và `fix_rounds = 1`; Settings đổi được editor model).

**Checkpoint**: commit.

---

## Phase 6: Polish

- [ ] T031 [P] Sửa `CLAUDE.md`:
  - mục Cấu trúc: thêm `tools/filmcheck/` và lệnh `script`, `web fetch`, `qc`, `config`;
  - test: `sh tests/filmcheck/run.sh`.

  Sửa `specs/003-studio-ui/contracts/cli.md` cho các lệnh mới. Cập nhật bộ nhớ dự án: chạy 5 bộ test.
- [ ] T032 [P] Dựng lại ảnh `studio-job` và `studio-web` (`sh bin/studio online up` hoặc `docker build`). Kiểm trong container: `sh bin/studio script check` và `qc` chạy được trên phim mẫu (`node`, `ffmpeg`, `fc-list` có sẵn). Sửa `deploy/job.Dockerfile` nếu thiếu gói (ví dụ `fonttools` theo T001).
- [ ] T033 Chạy 5 bộ test; sửa tới khi đạt.
- [ ] T034 Chạy quickstart bằng tay (bước 1–3) với tài khoản thật: một phim local và một phim online (Docker), 45–60 giây có lời đọc và số liệu, có chọn duyệt treatment. Ghi kết quả vào task này: điểm từng lượt, số đo QC, tổng token của việc và phần token của bước kịch bản (SC-005 ≤ 15%), đạt / đạt một phần / thất bại (hiến pháp IV).

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → US1 → US2 → US3 → Polish. US2 dùng `report.py` (T004) và cổng QC; không cần US1 để chạy `qc` trên phim mẫu, nhưng phần worker (T026) dựa vào T018.
- Trong US1: T008 → T009 → T010 → T011; T012 sau T006, T007; T013 sau T009–T012; T014 sau T005; T016–T019 sau T013–T014; T020 cuối.
- Trong US2: T021, T022, T023 song song được (cùng tệp `qc.py`, nên làm tuần tự nếu một người); T024 → T025 → T026 → T027.

## Parallel Example

```text
Phase 1: T002, T003 cùng lúc.
Phase 2: T005, T006, T007 cùng lúc (khác tệp); T004 riêng.
Phase 6: T031, T032 cùng lúc.
```

## Implementation Strategy

1. **MVP = Phase 1–3** (US1): kịch bản được chấm và chặn trước khi thu giọng. Dừng, chạy 5 bộ test, commit, cho người dùng xem.
2. Thêm US2 (QC), rồi US3 (theo dõi). Mỗi story một commit.
3. Polish và bài chạy thật T034 trước khi tạo PR.
