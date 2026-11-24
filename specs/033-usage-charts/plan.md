# Implementation Plan: Ô tổng và biểu đồ ở Settings → Usage

**Branch**: `033-usage-charts` | **Date**: 2026-11-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/033-usage-charts/spec.md`

**Mức quy trình**: Nhẹ (3 tệp code + 1 tệp test; chỉ thêm trường vào một API của chủ xưởng, không đổi dữ liệu). Bỏ `research.md` và `contracts/`; hình dạng API mới nằm trong [data-model.md](data-model.md).

## Summary

1. **API** (`tools/studio/studio/api_online.py`, `GET /api/v1/admin/usage`): giữ mọi trường cũ, thêm:
   - `tiles`: `{today, d7, d30}`, mỗi mục `{calls, tokens}`. Luôn tính tới hôm nay theo giờ Việt Nam, không theo `from`/`to`.
   - `days_by_via`: một dòng cho mỗi ngày trong khoảng (đủ ngày, ngày trống = 0) `{day, via: {<via>: {calls, tokens}}}`.
   - `vias`: danh sách nguồn có trong khoảng, thứ tự cố định (`plan:1`…`plan:5`, rồi `api`).
   - Kiểm khoảng: ngoài luật cũ (YYYY-MM-DD, from ≤ to), thêm tối đa 366 ngày → 422.
   - Một câu SQL `GROUP BY ngày, via` trên bảng `call` (đã có chỉ mục `call_via (via, at)`), một câu cho ô tổng.
2. **Giao diện** (`tools/studio/studio/web/app.js`, hàm `settingsUsage`):
   - Bộ chọn khoảng: nút 7 / 30 / 90 ngày và hai ô ngày "Từ"/"Đến" + "Áp dụng". Khoảng nằm trong hash `#/settings/usage?range=7` hoặc `?from=…&to=…` (giữ `q` tìm email). Khoảng sai → báo ở dòng trạng thái cạnh bộ chọn, không tải lại.
   - Ba ô tổng (Hôm nay / 7 ngày / 30 ngày): số request lớn, token ở dòng dưới.
   - Một biểu đồ cột xếp chồng vẽ bằng SVG, có nút chọn loại Requests / Tokens (đổi tại chỗ, không gọi lại API; loại nằm trong hash `metric=tokens`, mặc định requests), trong trang (không thêm thư viện, theo `Usage.tsx` của neb): mỗi cột một ngày, mỗi đoạn một nguồn; trục Y 4 vạch với số viết gọn (`1,2 tr`, `340 k`); nhãn ngày thưa dần khi nhiều cột; `<title>` + chú giải nổi khi rê chuột/chạm/focus (cột có `tabindex=0`); chú thích dưới biểu đồ (màu, tên nguồn + email, tổng); nút "Xem dạng bảng" bật/tắt bảng số.
   - Ba bảng hiện có và dòng tổng dùng cùng khoảng (gọi `/admin/usage?from=&to=`).
3. **CSS** (`tools/studio/studio/web/style.css`): `.tiles`, `.chart`, `.legend`, `.chart-tip`, `.range`; 6 màu nguồn là biến CSS `--via-1`…`--via-5`, `--via-api`, có bộ màu riêng cho chế độ tối; khung biểu đồ `width:100%` để co ở 390 px.
4. **Test** (`tests/online/test_admin.py`): API với dữ liệu `call` giả ở nhiều ngày và nhiều nguồn (ô tổng, đủ ngày, số theo nguồn, khoảng > 366 ngày → 422, khách bị chặn); thêm bước trình duyệt (Playwright, như `AdminBrowser`) mở Usage, kiểm 3 ô, số cột, chú thích, bảng dạng số, đổi loại sang Tokens, đổi sang 7 ngày, bề ngang 390 px không cuộn ngang.

## Technical Context

**Language/Version**: Python 3.12 (FastAPI) cho API; JavaScript thuần (ES2022, không bundler) cho trang

**Primary Dependencies**: Không thêm. SQLite (bảng `call` có sẵn); SVG của trình duyệt

**Storage**: Không đổi. Chỉ đọc bảng `call`

**Testing**: `unittest` trong `tests/online/` (Studio giả + Playwright có sẵn); chạy `sh tests/online/run.sh`, `sh tests/ui/run.sh`

**Target Platform**: Trình duyệt (máy tính và điện thoại) mở app desktop hoặc bản online

**Project Type**: dịch vụ web (API + trang một tệp)

**Performance Goals**: 90 ngày × 6 nguồn ≈ 540 đoạn SVG; API < 300 ms với 50.000 lượt gọi (một câu GROUP BY có chỉ mục)

**Constraints**: Không thư viện ngoài; đọc được ở 390 px và chế độ tối; chỉ chủ xưởng

**Scale/Scope**: ≤ 366 cột, ≤ 6 nguồn

## Constitution Check

| Nguyên tắc | Đánh giá |
|---|---|
| I. Spec là nguồn sự thật | Đạt: spec không nhắc công nghệ; công nghệ chỉ ở đây |
| II. Không đoán | Đạt: phạm vi đã hỏi người dùng (chỉ "Ô tổng + biểu đồ"); không thêm tách loại token hay hạn mức |
| III. MVP, chia story | Đạt: một story P1, tự test được |
| IV. Đo được | Đạt: SC-002 kiểm khớp 100% bằng test tự động; SC-004 đo cuộn ngang bằng trình duyệt |
| V. Đơn giản | Đạt: không thư viện biểu đồ, không bảng mới |
| VI–IX | Không liên quan (không đụng `lib/`, dựng hình, học phong cách, phim) |

Sau thiết kế: không đổi, không có vi phạm.

## Project Structure

### Documentation (this feature)

```text
specs/033-usage-charts/
├── spec.md
├── plan.md
├── data-model.md      # hình dạng trả về mới của /admin/usage
├── quickstart.md
├── checklists/requirements.md
└── tasks.md           # /speckit-tasks
```

### Source Code (repository root)

```text
tools/studio/studio/
├── api_online.py      # usage(): tiles, days_by_via, vias, giới hạn 366 ngày
└── web/
    ├── app.js         # settingsUsage(): bộ chọn khoảng, ô tổng, 2 biểu đồ SVG, chú thích, bảng
    └── style.css      # .tiles .chart .legend .chart-tip .range, màu nguồn sáng/tối
tests/online/
└── test_admin.py      # API + trình duyệt cho Usage
```

**Structure Decision**: Sửa tại chỗ trong các tệp đang chứa trang Usage; không tạo mô-đun mới.

## Complexity Tracking

Không có.
