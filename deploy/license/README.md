# Máy chủ license của app desktop

Máy chủ này cấp license key cho app desktop claude-Utube. Nó cũng chuyển bản phát hành riêng tư trên GitHub tới app của người có key, để app tự cập nhật (specs/017). Máy chủ chạy trên một VPS nhỏ của chủ xưởng, có tên miền và HTTPS.

> License chỉ chặn người dùng bình thường: người sửa được mã của app vẫn vượt qua được.

## 1. Chuẩn bị

- Một VPS Ubuntu 24.04 nhỏ (1 CPU, 1 GB RAM là đủ) có địa chỉ IP công khai. Cài Docker Engine và plugin `docker compose`: https://docs.docker.com/engine/install/ubuntu/
- Một tên miền, ví dụ `license.example.com`, có bản ghi A trỏ về IP của VPS. Mở cổng 80 và 443.
- Repo này trên VPS:

  ```bash
  git clone <repo> && cd claude-Utube
  ```

## 2. Tạo khoá ký

```bash
docker build -f deploy/license/license.Dockerfile -t claude-utube-license .
docker run --rm -v "$PWD:/out" -u "$(id -u)" claude-utube-license python cli.py keygen --out /out/signing.key
```

Lệnh này in ra **khoá công khai**, và ghi **khoá riêng** vào `signing.key`.

- **Khoá công khai** chép vào tệp `desktop/license-public-key.txt` của repo, rồi commit. Mọi app build sau đó dùng khoá này để kiểm license.
- **Khoá riêng** (dòng trong `signing.key`):
  - dán vào `LICENSE_SIGNING_KEY` trong `deploy/license/.env` (bước 3);
  - dán vào secret của repo trên GitHub: Settings → Secrets and variables → Actions → New repository secret, tên `LICENSE_SIGNING_KEY`;
  - **sao lưu** vào một chỗ an toàn ngoài VPS, rồi xoá `signing.key` khỏi VPS. Mất khoá riêng thì phải phát hành lại app cho mọi người.

## 3. Cấu hình và chạy

```bash
cp deploy/license/.env.example deploy/license/.env
nano deploy/license/.env        # DOMAIN, LICENSE_SIGNING_KEY, GITHUB_REPO, GITHUB_TOKEN
mkdir -p deploy/license/data && sudo chown 1000:1000 deploy/license/data
docker compose -f deploy/license/compose.yaml --env-file deploy/license/.env up -d --build
curl https://license.example.com/health      # {"ok":true}
```

`GITHUB_TOKEN` là một fine-grained token tạo ở GitHub → Settings → Developer settings → Fine-grained tokens. Chỉ chọn repo này, quyền **Contents: Read-only**. Token chỉ nằm trên VPS.

## 4. Mật khẩu quản trị

```bash
docker compose -f deploy/license/compose.yaml --env-file deploy/license/.env exec license python cli.py admin-password
```

Tự gõ mật khẩu (ít nhất 12 ký tự) trong terminal của VPS; mật khẩu không bao giờ hiện ra. Rồi mở `https://license.example.com/admin` để tạo key.

- **Tạo key**: nhập tên người hoặc nhóm, số máy, ngày hết hạn (bỏ trống là không hết hạn). Key chỉ hiện **một lần**: chép rồi gửi cho người dùng.
- **Thu hồi** (Turn off): app của người đó khoá trong tối đa 15 phút nếu có mạng, chậm nhất 7 ngày nếu mất mạng.
- **Gỡ máy** (Remove): chỗ của máy đó được trả lại, và máy đó bị từ chối. Bấm lần nữa (Allow again) để máy đó kích hoạt lại được.

## 5. Bật license trong bản build

Trên GitHub: Settings → Secrets and variables → Actions → **Variables** → New repository variable, tên `LICENSE_SERVER_URL`, giá trị `https://license.example.com`. Từ bản phát hành tiếp theo (gắn tag `desktop-vX.Y.Z`):

- app hỏi key ngay lần mở đầu;
- `release.json` được ký, nên các app có key tự nhận bản mới.

Không có biến này thì bản build không có license, cũng không tự cập nhật (như 0.1.0).

## 6. Sao lưu và nâng cấp

- Máy chủ tự sao lưu cơ sở dữ liệu mỗi ngày vào `deploy/license/data/backup/` và giữ 30 bản. Nên chép thư mục này ra ngoài VPS định kỳ.
- Nâng cấp máy chủ:

  ```bash
  git pull && docker compose -f deploy/license/compose.yaml --env-file deploy/license/.env up -d --build
  ```
