# Tasks: Ô tổng và biểu đồ ở Settings → Usage

**Input**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), [quickstart.md](quickstart.md)

**Tests**: Có (hiến pháp IV: logic quan trọng phải có test tự động; SC-002 và SC-004 đo bằng test).

## Phase 1: Setup

Không có: không thêm thư viện, không thêm tệp mới.

## Phase 2: Foundational

Không có: chỉ một story.

## Phase 3: User Story 1 - Nhìn nhanh lượng request và token (P1) 🎯 MVP

**Goal**: Ba ô tổng, bộ chọn khoảng ngày, hai biểu đồ cột xếp chồng theo nguồn gọi, chú thích, chú giải, bảng dạng số. Khoảng ngày áp dụng cho cả các bảng cũ.

**Independent Test**: Dữ liệu `call` giả trên nhiều ngày và nhiều nguồn (`plan:1`, `plan:2`, `api`). Mọi số trên API và trang khớp dữ liệu đã tạo; đổi sang 7 ngày thì còn 7 cột; ở 390 px không cuộn ngang.

### Tests

- [x] T001 [US1] Thêm test API trong tests/online/test_admin.py. Chèn dòng `call` giả hôm nay, hôm qua, 8 ngày trước và 40 ngày trước, với các nguồn `plan:1`, `plan:2`, `api`, rồi kiểm:
  - `tiles.today`, `tiles.d7`, `tiles.d30` đúng: "luôn tính tới hôm nay (giờ Việt Nam) … không phụ thuộc `from`/`to`".
  - `days_by_via` "có đúng một dòng cho mỗi ngày từ `from` đến `to`", ngày trống có `via` rỗng.
  - Số theo nguồn đúng; `vias` theo thứ tự `plan:1`, `plan:2`, `api`.
  - `?from=…&to=…` dài 367 ngày → 422 `invalid`; 366 ngày → 200.
  - Khách (không phải chủ xưởng) vẫn bị 403.
- [x] T002 [US1] Thêm test trình duyệt trong tests/online/test_admin.py (lớp `AdminBrowser`, Playwright). Mở `#/settings/usage` bằng chủ xưởng với dữ liệu của T001, rồi kiểm:
  - 3 ô `.tile` có số khớp `tiles`.
  - Biểu đồ request có 30 cột.
  - Chú thích có tên nguồn và tổng.
  - "Xem dạng bảng" ra bảng có số khớp.
  - Bấm "7 ngày": còn 7 cột, hash có `range=7`.
  - Khoảng tự chọn sai báo lỗi.
  - Viewport 390 px: `scrollWidth ≤ clientWidth`.
  - Không có lỗi console.

### Implementation

- [x] T003 [US1] Trong tools/studio/studio/api_online.py, hàm `usage()`:
  - Giới hạn khoảng tối đa 366 ngày tính cả hai đầu, quá thì 422 `invalid`.
  - Thêm `tiles` `{today, d7, d30}` mỗi mục `{calls, tokens}`. Dùng một câu SQL có `SUM(CASE …)` trên `VN_DAY_SQL`, ngày gốc là `quotas.today_vn()`.
  - Thêm `days_by_via`: một câu `GROUP BY VN_DAY_SQL, via`, điền đủ mọi ngày từ `from` đến `to`.
  - Thêm `vias`: `plan:<n>` sắp theo số, rồi `api`, rồi nguồn khác theo tên.
  - Giữ nguyên mọi trường cũ.
- [x] T004 [P] [US1] Trong tools/studio/studio/web/style.css:
  - Thêm `.range` (nhóm nút và ô ngày), `.tiles`/`.tile` (lưới tự xuống hàng), `.chart` (svg `width:100%`), `.legend`, `.chart-tip` (chú giải nổi).
  - Thêm biến màu `--via-1`…`--via-5`, `--via-api`, `--via-other`, có bộ màu riêng cho chế độ tối theo cách các biến màu hiện có.
- [x] T005 [US1] Trong tools/studio/studio/web/app.js, hàm `settingsUsage(top)`:
  - Đọc `range` (7 / 30 / 90) hoặc `from`/`to` từ hash (giữ `q`), mặc định 30 ngày. Tính `from`/`to` theo ngày Việt Nam và gọi `/admin/usage?from=&to=`.
  - Bộ chọn khoảng: nút 7 / 30 / 90 ngày, ô "Từ"/"Đến" kiểu date, nút "Áp dụng". Khoảng sai thì báo ở `#use-msg` và không đổi hash.
  - Ba ô tổng: Hôm nay / 7 ngày / 30 ngày.
  - Dòng tổng và ba bảng cũ dùng khoảng đã chọn (sửa chữ "Last 30 days" thành khoảng thật).
- [x] T006 [US1] Trong tools/studio/studio/web/app.js, thêm hàm `usageChart(id, title, rows, vias, metric, label)` để vẽ SVG cột xếp chồng:
  - Trục Y 4 vạch, số viết gọn (k, tr). Nhãn ngày thưa dần để không chồng nhau.
  - Mỗi cột là một `<g tabindex="0">` có `<title>`.
  - Chú giải nổi `.chart-tip` hiện khi rê chuột, chạm hoặc focus: ngày, số theo từng nguồn, tổng.
  - Chú thích dưới biểu đồ: màu, tên nguồn (`claudeLabel` + email, hoặc "API key"; slot không còn thì thêm "(removed)"), tổng trong khoảng.
  - Nút "Show as table" bật/tắt bảng (dòng = ngày, cột = nguồn + tổng).
  - Không có lượt gọi nào thì hiện "No Claude calls in this range."
  - Gọi hàm này hai lần, cho request và cho token.

**Checkpoint**: T001–T002 đạt; trang chạy đúng theo quickstart.md.

## Phase 3b: Thay đổi theo yêu cầu (2026-11-24): một biểu đồ, có nút chọn loại

- [x] T008 [US1] Trong tools/studio/studio/web/app.js: thay hai biểu đồ bằng một biểu đồ `#ch-usage` có nút chọn loại "Requests" (mặc định) / "Tokens" (`.seg`, `aria-pressed`). Đổi loại thì vẽ lại tại chỗ bằng dữ liệu đã có, không gọi lại API, ghi `metric=tokens` vào hash bằng `history.replaceState` (giữ `q`, `range`/`from`/`to`); đổi khoảng ngày vẫn giữ loại.
- [x] T009 [US1] Sửa tests/online/browser_usage.cjs: một biểu đồ, chuyển sang Tokens thì chú thích và bảng theo token, hash có `metric=tokens`, tải lại vẫn ở Tokens.

## Phase 4: Polish

- [x] T007 Chạy `sh tests/online/run.sh`, `sh tests/ui/run.sh`, `sh tests/run.sh`; xem thử thật theo quickstart.md (máy tính, 390 px, chế độ tối); tự đối chiếu FR-001…FR-010 và SC-001…SC-004, ghi kết quả vào cuối tasks.md.

## Dependencies

- T003 → T001, T005, T006
- T004 độc lập (khác tệp)
- T005 → T006 → T002
- T007 sau cùng

## Parallel

- T004 (CSS) chạy song song với T003 (API).

## Implementation Strategy

Chỉ một story (MVP). Thứ tự: T003 → T001 (API đúng) → T004 → T005 → T006 → T002 → T007.

## Kết quả kiểm chứng (T007, 2026-11-24)

- `sh tests/online/run.sh`: Ran 213, OK (skipped=2). Gồm `test_admin.UsageCharts` (API: ô tổng, đủ ngày, theo nguồn, 366/367 ngày, khách 403; trình duyệt: một biểu đồ, Requests ↔ Tokens tại chỗ, `metric=tokens` và `range=7` trong địa chỉ, tải lại giữ nguyên, khoảng sai báo lỗi, 390 px không cuộn ngang, không lỗi console).
- `sh tests/ui/run.sh`: Ran 77, OK; desktop node 33/33 (lần đầu bắt 9 lỗi kiểu trong app.js, đã sửa).
- `sh tests/run.sh`: PASS 87/87.
- SC-003: 50.000 lượt gọi trong 90 ngày, `/admin/usage` trả lời 152–159 ms.
- Xem thử: ảnh chụp chế độ sáng và tối, cột/trục/chú thích đọc rõ; bảng màu 6 nguồn qua trình kiểm màu (sáng và tối), 3 màu sáng dưới 3:1 được bù bằng chú thích + bảng số.

| Yêu cầu | Kết quả |
|---|---|
| FR-001 ô tổng | Đạt |
| FR-002 bộ chọn khoảng, trong địa chỉ | Đạt |
| FR-003 khoảng áp dụng cho biểu đồ, tổng, 3 bảng | Đạt |
| FR-004 một biểu đồ, chọn Request/Token | Đạt |
| FR-005 màu cố định, chú thích | Đạt |
| FR-006 chú giải rê chuột/chạm/focus | Đạt (rê chuột có test; chạm và focus kiểm bằng code) |
| FR-007 xem dạng bảng | Đạt |
| FR-008 ngày Việt Nam | Đạt |
| FR-009 chỉ chủ xưởng | Đạt |
| FR-010 390 px, chế độ tối | Đạt |
| SC-001…SC-004 | Đạt |
