# Chạy xưởng online

Hướng dẫn này đưa xưởng lên một máy chủ để khách tự đăng ký và làm phim trên web (specs/007).

> **Trước khi mở đăng ký cho công chúng, hãy hỏi luật sư.** Hiến pháp 2.1.0 cho phép tải video từ kênh YouTube khách nêu để học phong cách, nhưng chủ xưởng chịu rủi ro pháp lý (điều khoản của YouTube, bản quyền). Hãy sửa `deploy/terms.md` cho đúng với xưởng của bạn.

## 1. Chọn máy chủ

- Ubuntu 24.04, khoảng **8 vCPU, 16 GB RAM**, 200 GB ổ đĩa. Mỗi việc chạy dùng tới 4 CPU và 8 GB, mặc định chạy 2 việc cùng lúc.
- Cài Docker Engine và plugin `docker compose`: https://docs.docker.com/engine/install/ubuntu/
- Mở cổng 80 và 443.

## 2. Trỏ tên miền

Tạo bản ghi DNS `A` (và `AAAA` nếu có IPv6) từ tên miền, ví dụ `studio.example.com`, về địa chỉ IP của máy chủ. Caddy tự xin chứng chỉ HTTPS khi khởi động.

## 3. Điền `deploy/.env`

```sh
git clone <repo> claude-Utube && cd claude-Utube
cp deploy/.env.example deploy/.env
sudo mkdir -p /srv/studio/data && sudo chown 1000:1000 /srv/studio/data
```

Điền vào `deploy/.env`:
- `DOMAIN`: tên miền ở bước 2.
- `STUDIO_DATA_HOST`: thư mục dữ liệu, ví dụ `/srv/studio/data`. Tài khoản uid 1000 phải ghi được vào thư mục này.
- `ANTHROPIC_API_KEY`: khoá API. Khoá chỉ nằm ở dịch vụ `web` (để kiểm nội dung ý tưởng) và `proxy`. Container chạy việc không bao giờ thấy khoá này.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `MAIL_FROM`: máy chủ gửi thư (thư xác minh, quên mật khẩu, báo phim xong).

Không commit `deploy/.env`. Tệp này đã có trong `.gitignore`.

## 4. Bật xưởng

```sh
sh bin/studio online up            # lần đầu dựng ảnh studio-job khá lâu (khoảng 15–30 phút)
sh bin/studio online admin you@example.com    # tạo tài khoản quản trị (hỏi mật khẩu)
```

Mở `https://<tên miền>`, đăng nhập bằng tài khoản quản trị, rồi vào **Admin** để đặt:
- hạn mức mỗi tháng;
- trần chi phí mỗi ngày (mặc định 20 USD) và mỗi việc (mặc định 5 USD);
- số việc chạy cùng lúc;
- tắt hay mở đăng ký.

Các lệnh khác:
- `sh bin/studio online logs [web|worker|proxy]`: xem nhật ký.
- `sh bin/studio online down`: tắt xưởng.

Sau khi `git pull` bản mới, chạy lại `sh bin/studio online up`.

## 5. Sao lưu

Mọi dữ liệu nằm trong `STUDIO_DATA_HOST`:
- `studio.db`: tài khoản, việc, chi phí;
- `accounts/<id>/`: phim, phong cách và số đo của từng khách.

Sao lưu hằng ngày, ví dụ bằng cron:

```sh
D=/srv/studio/data; B=/srv/backup/$(date +%F); mkdir -p "$B"
sqlite3 "$D/studio.db" ".backup '$B/studio.db'"      # chép an toàn khi xưởng đang chạy
tar -C "$D" -czf "$B/accounts.tgz" accounts
```

Không cần sao lưu `jobs/`, `uploads/` và `tmp/`. Đó là dữ liệu tạm, xưởng tự xoá.

## Cách xưởng giữ an toàn

| Phần | Làm gì |
|---|---|
| `caddy` | HTTPS, HSTS, CSP; chuyển mọi yêu cầu tới `web` |
| `web` | giao diện và API; mỗi khách chỉ thấy dữ liệu của mình |
| `worker` | chạy việc trong container `studio-job`, mỗi việc một container. Worker gọi Docker qua `docker-proxy`; bộ lọc này chỉ cho tạo, chạy, xem, dừng, xoá container và đọc nhật ký. Worker không giữ `docker.sock` thật, và chỉ chạy ảnh `studio-job:*` |
| `proxy` | nơi duy nhất container việc gọi được. Proxy thay mã của việc bằng khoá thật, tính chi phí, và dừng việc khi vượt trần |
| `egress` | chỉ việc học từ YouTube đi qua đây, và chỉ tới các tên miền của YouTube |

**Rủi ro còn lại:** `docker-proxy` không chặn được việc gắn thư mục bất kỳ của máy chủ vào container. Vì vậy, ai chiếm được worker thì gần như có quyền trên máy chủ. Hãy giữ worker và máy chủ luôn được cập nhật.
