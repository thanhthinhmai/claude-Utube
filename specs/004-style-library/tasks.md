# Tasks: Thư viện phong cách trên Film Studio

**Input**: Design documents from `specs/004-style-library/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-library.md, quickstart.md

**Tests**: Có. Spec yêu cầu kiểm bằng test (SC-001, SC-006, SC-007) và các tính năng trước đều có test.

**Format**: `- [ ] [ID] [P?] [Story] Mô tả` · [P] = làm song song được (khác file, không phụ thuộc việc chưa xong)

## Phase 1: Setup

- [ ] T001 Thêm thư viện giả vào dự án tạm của test giao diện trong `tests/ui/helpers.py`: `lib/lemo-opuscar/.git/HEAD` chứa SHA 40 ký tự; `styles/art-deco/` (style.json đủ trường như research §4, `STYLE.md` có `<script>`, `poster.jpg`), `styles/woodcut/` (style.json, STYLE.md, **không** poster), `styles/_template/` (style.json), `styles/broken/` (style.json hỏng), `styles/BadName/`; `library.lock` với `LIB_REPO=https://github.com/lemomo-ai/lemo-opuscar.git`; phong cách riêng `demo-style` có `based_on: "art-deco"`

---

## Phase 2: Foundational (chặn mọi user story)

- [ ] T002 Bỏ dòng `!/styles/*/poster.jpg` khỏi `SPARSE` trong `bin/studio` (giữ các dòng loại `styles/*/demo/`, `styleboard/`, `docs/frames/`, `docs/cover.jpg`, `docs/opuscar98.jpg`)
- [ ] T003 Trong `cmd_setup` của `bin/studio`: với thư viện `ok` hoặc `outdated` (sau khi cập nhật), nếu `.git/info/sparse-checkout` khác `SPARSE` **hoặc** số `styles/*/poster.jpg` < số phong cách, in `↓ đang tải poster của phong cách…`, ghi danh sách mới, chạy `git -C "$LIB" sparse-checkout reapply`; thành công in `✓ đã có poster: <n>/<tổng>`; lỗi in `✗ poster chưa tải được (mất mạng?). Làm phim vẫn được; chạy lại: sh bin/studio setup` và **không** đổi mã thoát (contracts/api-library.md)
- [ ] T004 Thêm `count_posters` vào `bin/studio`; `status` in `Phong cách thư viện: <n> · poster: <p>/<n> · phong cách riêng: … · phim: …`; `status --json` thêm `"library_posters"` vào `counts`; thiếu poster không làm `status` báo chưa sẵn sàng
- [ ] T005 Thêm test vào `tests/run.sh`: thư viện giả có `styles/a/poster.jpg`, `styles/b/poster.jpg`; máy mới → có poster, vẫn không có `styles/a/demo`; máy cũ (ghi lại danh sách sparse cũ có `!/styles/*/poster.jpg`, `reapply`, xoá poster) → `setup` mã 0, in "đã có poster", có poster, không tải lại (inode `.git` giữ nguyên); kho tắt (`mv "$U" "$U.off"`) khi thiếu poster → mã 0 và in "poster chưa tải được"; `status` có `poster: 2/2`; `git -C "$L" status --porcelain` rỗng (SC-007)
- [ ] T006 Thêm phần thư viện vào `tools/studio/studio/resources.py`: `lib_dir()`, `library()` trả `{installed, version, styles, groups, posters: {have, total}, skipped}` theo data-model.md; mỗi style chỉ có `slug, num, en, cn, category (← category_en), film, line, uses, dur, has_poster, github_url`; `slug` khớp `^[a-z0-9-]{1,60}$` và khác `_template`; style.json thiếu, hỏng, hoặc thiếu `en` → bỏ qua và tăng `skipped`; sắp theo `num` dạng số; `groups` theo thứ tự xuất hiện đầu tiên; `github_url` theo research §5 (chỉ khi `LIB_REPO` là github.com; commit từ `.git/HEAD`)
- [ ] T007 Thêm `library_style(slug)` (thêm `style_html` = `to_html(STYLE.md)`) và `library_poster(slug)` vào `tools/studio/studio/resources.py`: tên sai mẫu → `StudioError("bad_name", …, 400)`; không phải phong cách hợp lệ của thư viện hoặc `_template` → `404 not_found`; chỉ đọc `style.json`, `STYLE.md`, `poster.jpg` trong `lib/lemo-opuscar/styles/<slug>/`
- [ ] T008 Thêm 3 điểm vào `tools/studio/studio/server.py`: `GET /api/v1/library`, `/library/styles/{slug}`, `/library/styles/{slug}/poster` (`FileResponse` `image/jpeg`, `Cache-Control: max-age=86400`, có `ETag`)
- [ ] T009 Cập nhật `specs/003-studio-ui/contracts/api-v1.md`: thêm 3 dòng của contracts/api-library.md vào bảng; thêm `lib/lemo-opuscar/styles/` vào danh sách thư mục được đọc; ghi `based_on_in_library` ở `/styles`

**Checkpoint**: API trả đúng dữ liệu thư viện; test OpenAPI của 003 (SC-007 cũ) vẫn đạt.

---

## Phase 3: User Story 1 - Xem và tìm phong cách trong thư viện (P1) 🎯 MVP

**Goal**: Trang Library có lưới thẻ, lọc nhóm, tìm, trang chi tiết.
**Independent Test**: Mở Library: đủ phong cách có poster; lọc nhóm; tìm "deco"; chi tiết có luật và link GitHub.

- [ ] T010 [P] [US1] Viết `tests/ui/test_library.py`: `/library` trả `art-deco` và `woodcut`, không có `_template`, `broken`, `BadName`; `skipped` = 1 (broken); `posters` = `{have: 1, total: 2}`; trường thừa (`frame_sec`, `line_cn`) không có; `github_url` = `https://github.com/lemomo-ai/lemo-opuscar/tree/<sha>/styles/art-deco`; chi tiết có `style_html` không chứa `<script>`; poster 200 `image/jpeg` có `Cache-Control`; `woodcut/poster` → 404; `_template` → 404; `BadName`, `..%2f..`, `a%2fb` → 400/404 và không trả nội dung file (SC-006); chưa có thư viện → `installed: false`; `/library` với 66 phong cách giả < 0,5 s
- [ ] T011 [US1] Sửa `tools/studio/studio/web/index.html`: thanh bên nhóm "Library" gồm **Library** (`#/library`, biểu tượng sách), **My styles** (`#/styles`, đổi tên từ Styles), **Measurements**
- [ ] T012 [US1] Thêm trang `#/library` vào `tools/studio/studio/web/app.js`: tiêu đề "Library" + câu dẫn có số phong cách và phiên bản; hàng viên lọc theo nhóm kèm số lượng ("All" đầu tiên); ô tìm (không phân biệt hoa thường và dấu, trên `en`, `cn`, `slug`, `uses`); lọc trên trình duyệt, không gọi lại máy chủ; trạng thái trong địa chỉ `#/library?group=…&q=…` (dùng `history.replaceState` khi gõ để không mất tiêu điểm); lưới thẻ: poster `loading="lazy" decoding="async"` hoặc ô thay thế có tên, số `#18`, tên, nhóm, phim mẫu, câu mô tả, viên mục đích dùng; không có kết quả → thông báo và nút "Clear filters"; `posters.have < total` → dòng gợi ý `sh bin/studio setup`; `installed: false` → hướng dẫn `sh bin/studio setup`; `skipped > 0` → dòng ghi số phong cách bị bỏ qua
- [ ] T013 [US1] Thêm trang `#/library/<slug>` vào `tools/studio/studio/web/app.js`: quay lại "Library" (giữ bộ lọc trước đó), poster lớn, số, nhóm, tên, tên tiếng Trung, phim mẫu và độ dài, câu mô tả, mục đích dùng, link "Watch the demo film on GitHub" (khi có `github_url`), luật `style_html`
- [ ] T014 [P] [US1] Thêm kiểu cho lưới thư viện vào `tools/studio/studio/web/style.css`: thẻ có poster 16:9 bo góc, số nhỏ màu tím, viên nhóm và mục đích dùng, thanh lọc dạng viên cuộn ngang trên điện thoại, ô tìm có biểu tượng, ô thay thế poster (nền tím nhạt, tên ở giữa), lưới 3 cột trên máy tính / 1 cột trên điện thoại

**Checkpoint**: US1 dùng được một mình.

---

## Phase 4: User Story 2 - Dùng một phong cách để làm phim (P2)

**Goal**: "Use this style" chép câu lệnh mẫu.
**Independent Test**: Bấm ở Art Deco → bộ nhớ tạm có câu lệnh chứa "Art Deco"; trang báo "Copied".

- [ ] T015 [US2] Thêm `copyPrompt(name, el)` vào `tools/studio/studio/web/app.js`: chép `Make a 40-second film in the <name> style about …` bằng `navigator.clipboard.writeText`; thành công → "✓ Copied: paste it into Claude Code"; lỗi → hiện ô chữ chỉ đọc chứa câu lệnh, đã bôi đen sẵn (research §6); không gọi API ghi nào (FR-011)
- [ ] T016 [US2] Gắn nút "Use this style" (nút chính màu đen) vào thẻ thư viện (không mở trang chi tiết khi bấm nút) và trang chi tiết trong `tools/studio/studio/web/app.js`

---

## Phase 5: User Story 3 - Phong cách riêng ở mục riêng, nối với thư viện (P3)

**Goal**: My styles có Use this style và link phong cách nền.
**Independent Test**: My styles chỉ có phong cách riêng; "based on" mở trang phong cách nền trong Library.

- [ ] T017 [P] [US3] Thêm `based_on_in_library` vào `styles()` và `style()` trong `tools/studio/studio/resources.py` (true khi `based_on` là slug hợp lệ có trong thư viện); thêm kiểm vào `tests/ui/test_library.py` (`demo-style` → true; đổi `based_on` thành `khong-co` → false)
- [ ] T018 [US3] Sửa trang `#/styles` và `#/styles/<slug>` trong `tools/studio/studio/web/app.js`: tiêu đề "My styles"; "based on <x>" là link `#/library/<x>` khi `based_on_in_library`; thêm nút "Use this style" (dùng `copyPrompt` với tên `en`); trang trống giữ hướng dẫn học phong cách

---

## Phase 6: Polish & Cross-Cutting

- [ ] T019 [P] Mở rộng `tests/ui/browser_check.cjs` (và dự án tạm trong `tests/ui/test_browser.py`): mở `#/library`, đếm thẻ, bấm viên nhóm → số thẻ giảm, gõ "deco" → còn 1, tải lại → vẫn 1; bấm thẻ → thấy luật; bấm "Use this style" (cấp quyền `clipboard-read`, `clipboard-write`) → bộ nhớ tạm chứa "Art Deco"; không có lỗi trang
- [ ] T020 [P] Cập nhật `README.md`: mục giao diện thêm Library và My styles; `setup` tải thêm 66 poster (22 MB), không tải phim mẫu
- [ ] T021 Chạy `sh tests/run.sh`, `sh tests/ui/run.sh`, `sh tests/learn/run.sh`; chạy `sh bin/studio setup` trên thư viện thật của phiên (máy cũ, thiếu poster) để kiểm FR-002 và SC-007; chụp Library, chi tiết, My styles (máy tính sáng, điện thoại tối) để xem; đo thời gian trang Library với 66 poster thật (SC-003); ghi kết quả vào cuối file này

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → US1 → US2 → US3 → Polish. US2, US3 chỉ cần US1 xong phần trang (T012, T013).
- T002 → T003 → T004 → T005 (cùng `bin/studio`, `tests/run.sh`).
- T006 → T007 → T008 → T009; T010 sau T001 và T008.
- T011, T012, T013, T015, T016, T018 cùng `app.js`/`index.html`: làm tuần tự.

### Parallel Opportunities

- T005 ∥ T006 (khác file); T010 ∥ T011; T014 ∥ T012; T017 ∥ T015; T019 ∥ T020.

## Implementation Strategy

1. MVP: Phase 1–3 (T001–T014) → mở trang Library, xem, lọc, tìm. Dừng kiểm tra.
2. Thêm US2 (T015–T016), rồi US3 (T017–T018).
3. Polish (T019–T021), ghi kết quả.
