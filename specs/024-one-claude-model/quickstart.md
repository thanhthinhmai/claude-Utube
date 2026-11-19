# Quickstart: kiểm chứng 024

## 1. Test tự động (không tốn tiền)

```sh
sh tests/filmcheck/run.sh     # test_one_model: quét mã (SC-002), models.py, config model (SC-003)
sh tests/online/run.sh        # Settings: 422 cho model ngoài danh sách và editor_model; GET có models (SC-003, SC-004)
sh tests/run.sh && sh tests/ui/run.sh && sh tests/learn/run.sh   # SC-005
```

Kỳ vọng: tất cả đạt.

## 2. Lệnh chat

```sh
sh bin/studio config model                     # in: claude-opus-5-5
sh bin/studio config model claude-opus-5-5     # mã 0
sh bin/studio config model claude-haiku-5-5    # mã 2, stderr nêu danh sách, .studio/config.json không đổi
```

## 3. Lượt thật có tìm web (SC-001, tốn ít token)

Chạy một vòng biên tập trên một phim có `SCRIPT.md` (ví dụ `pause-ten-seconds`, thư mục tạm):

```sh
sh bin/studio script review <phim>
```

Đọc `.check/review-r<n>.json` mới nhất: `model` = `claude-opus-5-5`. Kiểm `modelUsage` của lượt (ghi trong `usage` thô hoặc chạy lại lệnh `claude -p` mẫu ở plan R2): chỉ một khoá `claude-opus-5-5`.

## 4. Giao diện (online/app)

Mở Settings → General: một ô chọn "Claude model" (Opus 5.5), không có "Script editor model".
