# Contract: lệnh `topics` và `config youtube-key`

Các lệnh chạy ở local, với gốc là `STUDIO_ROOT`. Thông báo in ra bằng tiếng Anh, ngắn. Với `--json`, lệnh in đúng một đối tượng JSON.

| Lệnh | Việc | Mã thoát |
|---|---|---|
| `config youtube-key` | nhập khoá kín (getpass), thử khoá, rồi lưu vào `~/.config/claude-utube/youtube.key` (quyền 600). Không bao giờ in khoá; chỉ in 4 ký tự cuối | 0 · 2 khi khoá không dùng được |
| `topics score <channel> "<đề>" … [--file F] [--suggest] [--json]` | chấm tối đa 20 đề (cộng tối đa 10 đề gợi ý khi có `--suggest`), gộp vào `topics.json`, viết `TOPICS.md`, in bảng điểm | 0 · 2 khi thiếu khoá, kênh không có, hay đầu vào sai · 3 khi hết hạn mức giữa chừng (các đề đã chấm vẫn được lưu) |
| `topics queue <channel> [--all] [--json]` | in hàng đợi; có `--all` thì in thêm các đề bị chặn, DROP, đã làm | 0 |
| `topics take <channel> [--film <name>] [--allow-stale]` | lấy đề theo R4, chuyển sang `in_progress`, in chữ của đề để dùng làm ý tưởng phim | 0 · 1 khi không còn đề nào lấy được (in lý do) |
| `topics made <channel> <n>` | `in_progress` → `made` | 0 · 2 |
| `topics type <channel> <n> <type>` | sửa kiểu đề | 0 · 2 |
| `topics fit <channel> <n> <0-10>` | sửa điểm "hợp kênh"; tính lại tổng và kết luận | 0 · 2 |
| `topics recheck <channel> [<n>…]` | chấm lại số liệu (dùng số liệu tạm 24 giờ khi còn) | như `score` |
| `topics refs <channel> [--add UC…] [--remove UC…]` | đặt danh sách kênh mẫu (tối đa 10). Không có tham số thì in danh sách | 0 · 2 |
| `topics usage` | in số đơn vị đã dùng hôm nay và giới hạn | 0 |

**Bảng điểm in ra**, mỗi đề một dòng:
```
#3 GO 36/50  demand 8 · heat 6 · competition 6 · overlap 9 · fit 7  [explainer]  "Why honey never spoils"
   top: "The honey in the pharaoh's tomb" · 2.1M views · 140 days
```

**Không bao giờ in khoá**. Mọi thông báo lỗi từ YouTube đi qua `redact` trước khi in.
