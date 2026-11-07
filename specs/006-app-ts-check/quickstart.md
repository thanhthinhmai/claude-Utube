# Quickstart: kiểm tra 006

## Test

```sh
sh tests/ui/run.sh
```

Bộ test có thêm `test_typecheck`. Có mạng thì test đạt với 0 lỗi. Không có mạng thì test báo `skipped` kèm lý do.

Chạy riêng:

```sh
tools/.venv/bin/python -m unittest discover -s tests/ui -t tests/ui -k typecheck -v
```

## Thử một lỗi (SC-002)

Thêm tạm cuối `app.js` dòng `document.title = 5;`, chạy lệnh trên: test thất bại và in `app.js(<dòng>,…): error TS2322`. Xoá dòng đó.

## VS Code

Mở `tools/studio/studio/web/app.js`: không có gạch đỏ. Gõ thử `document.title = 5;` thì thấy gạch đỏ ngay.

## Không đổi hành vi

```sh
sh tests/run.sh
sh tests/learn/run.sh
```

Cùng với `tests/ui/run.sh` (gồm test trình duyệt): tất cả đạt.
