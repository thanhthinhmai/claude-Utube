# Research: Chế độ Client (018)

## R1. Cổng chia sẻ trong app Host

- **Máy chủ**: `https.createServer({cert, key})` nghe `0.0.0.0:<cổng>`, cổng mặc định 47860 (đổi được nếu bận).
- **Yêu cầu của Client đã ghép đôi** (header `X-CU-Client: <clientId>.<token>`):
  - `http.request` tới `127.0.0.1:<cổng web>`, giữ nguyên method, đường dẫn, header (gồm `Host`, nên phần lõi kiểm `Origin` khớp `Host` như chế độ online);
  - bỏ header `X-CU-Client` trước khi chuyển;
  - nối luồng hai chiều, nên SSE và tải tệp lớn đều chạy.
- **Đường riêng của cổng** (`/__cu/*`):
  - `hello`;
  - `pair` và `pair/confirm`;
  - `update` và `update/<tên>`.
- **Yêu cầu không có `X-CU-Client` hợp lệ**: `403`.
- **Tắt chia sẻ**: `server.close()` cùng `closeAllConnections()`.
- **Windows**: app chạy phía Windows, nên `127.0.0.1:<cổng web>` đi vào WSL2 nhờ cơ chế chuyển localhost (015 R1).

## R2. Ghép đôi gắn với dấu vân tay

- **Mã ghép đôi**: 10 ký tự từ bảng 31 ký tự của 017 (khoảng 50 bit), hiện dạng `XXXXX-XXXXX`.
  - Mã chỉ có hiệu lực 10 phút sau khi chủ xưởng bấm "Add a computer".
  - Mã nằm trong bộ nhớ của app Host, không ghi ra tệp.
- **Dấu vân tay**: `fp` là sha256 (hex) của chứng chỉ DER. Host biết `fp_host`; Client đọc `fp_seen` từ kết nối TLS (`socket.getPeerCertificate().raw`).
- **Các bước**:
  1. Client `POST /__cu/pair {nonceC, name}`. Host trả `{hostId, nonceH, proofH}`, với `proofH = HMAC_SHA256(code, "host|" + fp_host + "|" + nonceC + "|" + nonceH)`.
  2. Client tính lại `proofH` bằng `fp_seen`. Không khớp thì nghĩa là mã sai, hoặc có máy đứng giữa với chứng chỉ khác; Client dừng và **không gửi gì thêm**.
  3. Client `POST /__cu/pair/confirm {nonceH, proofC}`, với `proofC = HMAC(code, "client|" + fp_seen + "|" + nonceC + "|" + nonceH)`. Host tính lại bằng `fp_host`. Khớp thì Host cấp `{clientId, token}` (token 32 byte ngẫu nhiên) và lưu `sha256(token)`.
- **Giới hạn**:
  - `nonceH` chỉ dùng một lần và hết hạn sau 2 phút;
  - mỗi địa chỉ được sai `confirm` tối đa 10 lần trong 10 phút;
  - sau 5 lần sai trên cùng một mã, mã bị huỷ.
- **Máy đứng giữa** dùng chứng chỉ khác, nên có `fp` khác. Muốn tạo được `proofH` khớp với chứng chỉ của nó thì phải biết mã. Muốn dò mã khi không có mạng thì phải dò khoảng 2^50 trong vòng 10 phút: không khả thi.

## R3. Client trong Electron

- `session.defaultSession.setCertificateVerifyProc`: với tên máy và cổng của Host, chấp nhận khi `sha256(cert.data DER)` khớp `fp` đã lưu, còn lại từ chối. Chứng chỉ của các trang khác do Chromium kiểm như bình thường.
- `session.webRequest.onBeforeSendHeaders`, lọc theo URL của Host: thêm `X-CU-Client`.
- Cửa sổ chính mở `https://<địa chỉ>:<cổng>/`.
  - Không nối được (`did-fail-load` hay lỗi chứng chỉ) thì hiện `offline.html`, có "Try again" và "Change address".
  - Lỗi chứng chỉ thì báo "This is not the studio you paired with".
- **Ghép đôi lúc thiết lập**: dùng Node `https` với `rejectUnauthorized: false`, tự kiểm `fp`, thực hiện R2, rồi lưu cấu hình.

## R4. Chứng chỉ

- `sh bin/studio app cert [--data D]`: nếu chưa có `<data>/share/cert.pem` và `key.pem` thì tạo:
  - khoá ECDSA P-256 (quyền 600);
  - chứng chỉ tự ký, CN `claude-Utube studio`, hạn 10 năm, SAN `localhost`.
- Lệnh in JSON `{"cert", "key", "fingerprint"}`. App Host gọi một lần khi bật chia sẻ, rồi lưu vào `share-cert.json`.
- Client không kiểm tên máy (chỉ kiểm dấu vân tay), nên đổi IP không cần chứng chỉ mới.

## R5. Cập nhật qua Host

- **Host**:
  - `GET /__cu/update` chuyển tiếp tới `<máy chủ license>/api/license/releases`;
  - `GET /__cu/update/<tên>` chuyển tiếp tới `/api/license/releases/<tên>`;
  - cả hai gắn `X-CU-Lease` (lease của Host) và chỉ dành cho Client đã ghép đôi.
- **Client** dùng `checkUpdates` của 017 với nguồn là Host. Client kiểm chữ ký `release.json` bằng khoá công khai trong app, nên Host không sửa được bản phát hành.
- Bản build không có license thì `/__cu/update` trả 404 và Client không tự cập nhật.

## R6. Địa chỉ hiện cho thành viên

`os.networkInterfaces()`, lấy các IPv4 không phải nội bộ.
- Địa chỉ trong `100.64.0.0/10` là Tailscale.
- Bỏ địa chỉ của WSL (`vEthernet (WSL…)`) và Docker.
- Mỗi địa chỉ hiện dạng `<ip>:<cổng>`.

## Kết quả khi làm (2026-11-12)

- Bộ test của `share.js` đạt cả 6 test, trong đó có:
  - máy giả làm Host bị phát hiện trước khi Client gửi bất cứ thứ gì;
  - bắt luồng byte qua một rơ-le TCP mà không thấy mật khẩu, cookie, mã hay token;
  - tắt chia sẻ thì cổng đóng dưới 2 giây.
- GitHub Actions trên Windows và macOS (lượt chạy 43073997590):
  - Host bật chia sẻ thật trong app (chứng chỉ do phần lõi giả cấp), ghép đôi một máy, rồi mở trang qua cổng;
  - Client ghép đôi với một Host giả, mở trang qua HTTPS đã ghim, nhận bản mới qua Host; Host tắt thì Client hiện trang offline.
- **Bài học**:
  - `electron-builder.yml` phải liệt kê mọi module mà `main.js` nạp. Thiếu `share.js` thì app đóng gói lỗi ngay lúc mở. Đã thêm test `package-files.test.js`.
  - Trên máy Windows của GitHub, phải đợi bộ cài chạy xong ngay trong bước gọi nó. Cách gọi bộ cài sau 3 giây qua PowerShell không chạy, nên quay về gọi thẳng như 017.
