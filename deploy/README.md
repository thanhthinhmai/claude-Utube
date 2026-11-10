# Chạy xưởng online

Hướng dẫn này đưa xưởng lên một máy chủ để **nhóm nội bộ** của bạn làm phim trên web (specs/007, specs/008). Xưởng chạy bằng gói Claude Pro hoặc Max của chủ xưởng; không có đăng ký công khai, chủ xưởng tự thêm từng người.

> **Chỉ dùng nội bộ.** Gói Claude là gói cá nhân: điều khoản của Anthropic không cho dùng nó để phục vụ khách hàng bên ngoài. Chủ xưởng chịu trách nhiệm giữ xưởng trong nhóm của mình. Muốn mở cho công chúng thì phải dùng khoá API (bản 007) và hỏi luật sư.
>
> Hiến pháp 2.1.0 cho phép tải video từ kênh YouTube để học phong cách, nhưng chủ xưởng chịu rủi ro pháp lý (điều khoản của YouTube, bản quyền). Hãy sửa `deploy/terms.md` cho đúng với xưởng của bạn.

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
- `ANTHROPIC_API_KEY`: **tuỳ chọn**. Xưởng chạy bằng gói Claude; khoá này chỉ dùng khi không còn tài khoản Claude nào nhận được lệnh gọi (cả tài khoản đều chạm hạn mức hoặc cần đăng nhập lại). Để trống thì những lúc đó việc chờ tối đa 15 giây rồi lỗi, và thành viên được trả lượt. Khoá chỉ nằm ở `web` và `proxy`; worker chỉ biết là có khoá; container chạy việc không bao giờ thấy nó.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `MAIL_FROM`: máy chủ gửi thư (quên mật khẩu, báo phim xong, báo tài khoản Claude cần đăng nhập lại). Không bắt buộc để chạy.

Không commit `deploy/.env`. Tệp này đã có trong `.gitignore`.

## 4. Bật xưởng

```sh
sh bin/studio online up            # lần đầu dựng ảnh studio-job khá lâu (khoảng 15–30 phút)
sh bin/studio online admin you@example.com    # tạo tài khoản chủ xưởng ngay (hỏi mật khẩu)
```

Tạo tài khoản chủ xưởng **ngay sau** `online up`. Khi chưa có chủ, ai mở trang đầu tiên cũng tạo được tài khoản chủ ở `https://<tên miền>/#/setup` (giống neb-creative-tool). Bạn cũng có thể tự mở trang đó để tạo, miễn là làm trước người khác.

Rồi đăng nhập và làm theo thứ tự:
1. **AI accounts** (cuối thanh bên): bấm **Sign in** → **Open the sign-in** → đăng nhập Claude Pro hoặc Max → Claude hiện một mã → dán vào ô **Code** → **Send**. Thêm tối đa 5 tài khoản bằng **Add account**; mỗi lần gọi đi qua tài khoản dùng ít nhất trong 5 giờ qua. Thanh 5 giờ và tuần hiện phần hạn mức đã dùng, đọc từ chính các lần gọi.
2. **Settings → Users**: **Add user** với email, mật khẩu và vai trò (Member hoặc Owner), rồi tự đưa mật khẩu cho người đó. Menu ⋯ có Reset password, đổi vai trò, Sign out everywhere, Turn off, Remove.
3. **Settings → General**: hạn mức phim mỗi tháng, trần token mỗi việc (mặc định 40 triệu), số việc chạy cùng lúc.
4. **Settings → Usage**: số lần gọi và token theo tài khoản Claude, theo thành viên, theo ngày. Chỉ phần đi qua khoá API mới có số tiền.

Khi một tài khoản Claude cần đăng nhập lại, trang AI accounts hiện **Needs sign-in** và chủ xưởng nhận một thư (nếu đã cài SMTP).

Các lệnh khác:
- `sh bin/studio online logs [web|worker|proxy]`: xem nhật ký.
- `sh bin/studio online down`: tắt xưởng.

Sau khi `git pull` bản mới, chạy lại `sh bin/studio online up`.

## 5. Sao lưu

Mọi dữ liệu nằm trong `STUDIO_DATA_HOST`:
- `studio.db`: tài khoản, việc, các lần gọi Claude;
- `accounts/<id>/`: phim, phong cách và số đo của từng thành viên;
- `claude/`: đăng nhập của các tài khoản Claude (quyền 700). **Giữ kín như mật khẩu**: ai có thư mục này dùng được gói Claude của bạn. Không sao lưu thì sau khi khôi phục chỉ cần đăng nhập lại trên AI accounts.

Sao lưu hằng ngày, ví dụ bằng cron:

```sh
D=/srv/studio/data; B=/srv/backup/$(date +%F); mkdir -p "$B"
sqlite3 "$D/studio.db" ".backup '$B/studio.db'"      # chép an toàn khi xưởng đang chạy
tar -C "$D" -czf "$B/accounts.tgz" accounts
tar -C "$D" -czf "$B/claude.tgz" claude && chmod 600 "$B/claude.tgz"     # tuỳ chọn, xem trên
```

Không cần sao lưu `jobs/`, `uploads/` và `tmp/`. Đó là dữ liệu tạm, xưởng tự xoá.

## Cách xưởng giữ an toàn

| Phần | Làm gì |
|---|---|
| `caddy` | HTTPS, HSTS, CSP; chuyển mọi yêu cầu tới `web` |
| `web` | giao diện và API; mỗi thành viên chỉ thấy dữ liệu của mình. Đăng nhập tài khoản Claude (chạy Claude Code) và kiểm nội dung ý tưởng qua gói, không lưu phiên |
| `worker` | chạy việc trong container `studio-job`, mỗi việc một container. Worker gọi Docker qua `docker-proxy`; bộ lọc này chỉ cho tạo, chạy, xem, dừng, xoá container và đọc nhật ký. Worker không giữ `docker.sock` thật, và chỉ chạy ảnh `studio-job:*` |
| `proxy` | nơi duy nhất container việc gọi được. Proxy thay mã riêng của việc bằng mã của tài khoản Claude dùng ít nhất (hoặc khoá API dự phòng), tự làm mới mã qua Claude Code, đổi tài khoản khi chạm hạn mức, ghi từng lần gọi, và dừng việc khi vượt trần token. Đăng nhập Claude (`/data/claude`) chỉ nằm ở `web` và `proxy`, không bao giờ vào container việc |
| `egress` | chỉ việc học từ YouTube đi qua đây, và chỉ tới các tên miền của YouTube |

**Rủi ro còn lại:** `docker-proxy` không chặn được việc gắn thư mục bất kỳ của máy chủ vào container. Vì vậy, ai chiếm được worker thì gần như có quyền trên máy chủ. Hãy giữ worker và máy chủ luôn được cập nhật.
