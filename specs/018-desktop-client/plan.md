# Implementation Plan: Chế độ Client của app desktop

**Branch**: `018-desktop-client` | **Date**: 2026-11-12 | **Spec**: [spec.md](spec.md)

## Summary

- **Host**: app Electron có thêm một **cổng chia sẻ** (`desktop/share.js`):
  - máy chủ HTTPS của Node, nghe trên mọi địa chỉ ở một cổng cố định (mặc định 47860);
  - chuyển mọi yêu cầu của Client đã ghép đôi vào phần lõi ở `http://127.0.0.1:<cổng web>`. Phần lõi không đổi cách nghe (014 FR-003).
- **Chứng chỉ**:
  - do phần lõi tạo bằng `cryptography` (đã có sẵn): lệnh mới `sh bin/studio app cert`, ghi vào `<data>/share/` và in ra PEM cùng dấu vân tay;
  - lý do: app không phải thêm gói tạo chứng chỉ, và trên Windows chứng chỉ nằm cùng dữ liệu của Host.
- **Ghép đôi** (R2): cả hai bên chứng minh cùng biết mã ghép đôi bằng HMAC gắn với dấu vân tay chứng chỉ mà mỗi bên thấy, nên mã không đi qua mạng.
  - Thành công thì Host cấp cho Client `clientId` và `token` (Host chỉ lưu mã băm).
  - Sau đó mọi yêu cầu của Client mang header `X-CU-Client`, do Electron gắn vào bằng `webRequest`. Client chấp nhận chứng chỉ của Host chỉ khi dấu vân tay khớp (`setCertificateVerifyProc`).
- **Client**: chế độ mới trong cấu hình (`mode: "client"`).
  - Không có phần lõi, không có license.
  - Cửa sổ chính mở URL HTTPS của Host. Mất kết nối thì hiện trang `offline.html`.
  - Cập nhật qua `/__cu/update/*` của Host: Host chuyển tiếp tới máy chủ license bằng lease của chính nó. Client kiểm chữ ký bằng khoá công khai của app (017).
- **Thiết lập**: màn hình thiết lập thêm bước chọn chế độ, và form nối vào Host cho Client.
- **Quản lý chia sẻ**: khay của Host có "Share with my team…", mở cửa sổ `share.html`: bật hoặc tắt, địa chỉ, "Add a computer" (mã 10 phút), danh sách Client và nút gỡ.

## Technical Context

**Language/Version**: JavaScript (Electron 33, Node 20: `https`, `http`, `crypto`, `net`); Python 3.12 cho `app cert`.

**Primary Dependencies**: không thêm gói nào.

**Storage**:
- app Host: `config.json` có thêm `share` (bật hay tắt, cổng, danh sách Client với mã băm token), và `<userData>/share-cert.json` (PEM do phần lõi tạo, quyền 600);
- app Client: `config.json` có thêm `mode`, `host` (địa chỉ, dấu vân tay, `clientId`, `token`).

**Testing**:
- Node: `desktop/test/share.test.js` (ghép đôi, chặn sai mã, máy giả làm Host, không thấy mật khẩu trong luồng dữ liệu, tắt chia sẻ đóng cổng, chuyển tiếp cập nhật);
- Python: `app cert` trong `tests/online/test_host.py`;
- smoke Electron ở chế độ Client, nối vào một Host giả (`desktop/test/fake-host.mjs`).

**Target Platform**: như 016. Client chạy trên Windows hoặc macOS mà không cần WSL2.

**Constraints**:
- Phần lõi vẫn chỉ nghe ở `127.0.0.1`.
- Không cần quyền quản trị.
- Tường lửa có thể hỏi một lần; đó là hộp hỏi của hệ điều hành, app không đổi gì của hệ thống.

**Scale/Scope**: dưới 20 Client.

## Constitution Check

| Nguyên tắc | Kết quả |
|---|---|
| I, II | ✓ 3 câu đã chốt. Điều chưa chắc là WSL2 chuyển `127.0.0.1` của Windows vào bản Linux: 015 đã dựa vào điều này cho cửa sổ chính, nên cổng chia sẻ (chạy phía Windows) dùng được cùng đường đó |
| III | ✓ US1 + US2 tự đứng được; US3 thêm sau |
| IV | ✓ SC-002, 003, 004, 005 kiểm tự động; SC-001 bằng tay |
| V | ✓ Không thêm gói npm. Chứng chỉ dùng thư viện Python đã có. Một module `share.js` cho cả hai phía |
| Phần mềm hệ thống | ✓ Không cài và không đổi cấu hình hệ thống (không `netsh`, không sửa tường lửa) |
| Bảo mật, điều khoản | ✓ Mã hoá, ghép đôi có giới hạn, token chỉ lưu mã băm. Nhắc "chỉ chia cho nhóm nội bộ" vì đây là gói Claude cá nhân |

## Project Structure

```text
desktop/share.js          # logic: mã ghép đôi, HMAC, token, địa chỉ, cổng HTTPS + chuyển tiếp, chuyển tiếp cập nhật
desktop/share.html        # cửa sổ quản lý chia sẻ (Host)
desktop/offline.html      # Client không nối được Host
desktop/setup.html · main.js · preload.js · core.js   # chọn chế độ, form Client, chế độ Client
desktop/test/share.test.js · fake-host.mjs · vectors/share-cert.json (chứng chỉ thử)
tools/studio/studio/host.py · studio_cli.py           # app cert
.github/workflows/desktop.yml                         # smoke Client
```

## Complexity Tracking

| Vi phạm | Vì sao cần | Cách đơn giản hơn bị loại vì |
|---|---|---|
| Cổng chia sẻ là một máy chủ HTTPS trong app (thay vì cho phần lõi nghe mạng) | Windows: máy khác không vào thẳng được WSL2 nếu không có quyền quản trị; cần mã hoá và ghép đôi | Cho phần lõi nghe `0.0.0.0` thì không chạy được trên Windows nếu không dùng `netsh` (cần quyền quản trị), và vẫn chưa có mã hoá |
