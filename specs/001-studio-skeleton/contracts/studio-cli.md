# Contract: `bin/studio`

Chạy bằng `sh bin/studio <lệnh>` (hoặc `bin/studio <lệnh>` nếu có quyền chạy), từ bất kỳ thư mục nào.

## `setup`

- Đọc `library.lock`, kiểm tra công cụ, rồi đưa thư viện về trạng thái `ok`.
- **Đầu ra** (stdout, tiếng Việt): bảng công cụ, dòng trạng thái thư viện, kết luận `✓ sẵn sàng` hoặc `✗ chưa sẵn sàng` cùng việc cần làm.
- **Mã thoát**:
  - `0`: thư viện `ok` và không thiếu công cụ.
  - `1`: thư viện `foreign` hoặc `modified`; tải thất bại; hoặc thiếu hay cũ công cụ (thư viện vẫn được tải nếu được).
  - `2`: `library.lock` thiếu hoặc sai.
- **Không** sửa file nào trong thư viện đã có. **Không** cài phần mềm hệ thống.

## `status [--json]`

- Không dùng mạng, không ghi file.
- **Đầu ra mặc định**: bảng dễ đọc.
- **Đầu ra `--json`**: một object theo `StudioStatus` ([data-model.md](../data-model.md)), ví dụ:

```json
{"ready":true,"library":{"path":"lib/lemo-opuscar","state":"ok","commit_expected":"bebbbe1…","commit_found":"bebbbe1…"},"tools":[{"name":"git","found":"2.43","min":"2.25","state":"ok"}],"counts":{"library_styles":66,"my_styles":0,"films":0},"deps_core":false}
```

- **Mã thoát**: `0` sẵn sàng · `1` chưa sẵn sàng · `2` sai cách dùng.

## `deps [voice] [music]`

- Yêu cầu thư viện ở trạng thái `ok`; nếu không thì thoát mã 1 kèm gợi ý chạy `setup`.
- Chạy trình cài gói của thư viện với `LEMO_OPUSCAR_HOME` trỏ vào `lib/lemo-opuscar`. Mã thoát giữ nguyên của trình cài.

## `help` / không có đối số

- In cách dùng, mã thoát `0` (`help`) hoặc `2` (lệnh lạ).
