# Data model: 033 Ô tổng và biểu đồ Usage

Không có bảng mới. Mọi số lấy từ bảng `call` (specs/008): `at` (UTC), `via` (`plan:<slot>` hoặc `api`), `account_id`, `job_id`, `tokens_in`, `tokens_out`, `cache_write`, `cache_read`.

- **Ngày** = `date(at, '+7 hours')` (giờ Việt Nam, như hiện nay).
- **Request** = một dòng `call`.
- **Token** = `tokens_in + tokens_out + cache_write + cache_read`.

## `GET /api/v1/admin/usage?from=YYYY-MM-DD&to=YYYY-MM-DD` (chỉ chủ xưởng)

Trường cũ giữ nguyên (`from`, `to`, `days`, `by_account`, `by_claude`, `calls_total`, `tokens_total`, `cost_usd_total`, `storage_mb_total`). Thêm:

```json
{
  "tiles": {
    "today": {"calls": 12, "tokens": 300000},
    "d7":    {"calls": 52, "tokens": 1400000},
    "d30":   {"calls": 210, "tokens": 6100000}
  },
  "vias": ["plan:1", "plan:2", "api"],
  "days_by_via": [
    {"day": "2026-11-23", "via": {"plan:1": {"calls": 30, "tokens": 800000}}},
    {"day": "2026-11-24", "via": {}}
  ]
}
```

Luật:
- `tiles` luôn tính tới hôm nay (giờ Việt Nam): `today` = hôm nay, `d7` = hôm nay và 6 ngày trước, `d30` = hôm nay và 29 ngày trước. Không phụ thuộc `from`/`to`.
- `days_by_via` có đúng một dòng cho mỗi ngày từ `from` đến `to`, theo thứ tự tăng dần. Ngày không có lượt gọi thì `via` rỗng.
- `vias`: các nguồn xuất hiện trong khoảng, sắp `plan:1`…`plan:5` theo số, rồi `api`, rồi nguồn lạ (nếu có) theo tên.
- Khoảng không hợp lệ (sai dạng, `from > to`, hoặc dài hơn 366 ngày tính cả hai đầu) → 422 `invalid`.
