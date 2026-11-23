# Quickstart: kiểm chứng 030

Cần: `sh bin/studio deps online`.

```bash
# Test riêng của tính năng
sh tests/online/run.sh -k Rotation -k Thrift

# 5 bộ test của xưởng (SC-006)
sh tests/run.sh
sh tests/learn/run.sh
sh tests/ui/run.sh
sh tests/filmcheck/run.sh
sh tests/online/run.sh
```

Kết quả mong đợi:
- `Rotation`: một việc ở lại một tài khoản khi thứ tự "dùng ít nhất" đảo (SC-001); 429 chuyển ngay và ở lại tài khoản mới (SC-002); hai việc mới chia sang hai tài khoản (SC-003); 10 việc vẫn chia đều trong 20%.
- `Thrift`: env của việc có `CLAUDE_CODE_AUTO_COMPACT_WINDOW=300000`, `BASH_MAX_OUTPUT_LENGTH=20000` hoặc giá trị đặt riêng (SC-004); `rules()` có mục hướng dẫn gọn; `save_compact_state()` ghi tệp ≤ 8 KB trong < 1 s và không ném lỗi khi thư mục chỉ đọc (SC-005).

Sau khi triển khai lên VPS (không chạy trong spec này, tốn tiền): xem nhật ký gọi Claude (Settings → Worker / bảng `call`) — các lượt của một việc cùng `via`, `cache_read` chiếm phần lớn token vào.
