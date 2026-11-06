# claude-Utube

Xưởng phim cho Claude:
- **Học phong cách** của một kênh YouTube bằng cách đo từng khung hình, rồi lưu thành phong cách dùng lại được.
- **Làm phim bằng code** theo phong cách đã học, hoặc theo 66 phong cách có sẵn trong thư viện [lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar).

Dự án được xây theo quy trình [GitHub Spec Kit](https://github.com/github/spec-kit).

## Bắt đầu

Cần: git, Node 20+, ffmpeg 7+, Python 3.11+ (hoặc [uv](https://docs.astral.sh/uv/)); macOS, Linux hoặc WSL. Học phong cách chỉ cần ffmpeg 4.4+ và Python.

```sh
git clone https://github.com/thanhthinhmai/claude-Utube.git
cd claude-Utube
sh bin/studio setup        # tải thư viện đúng phiên bản, báo công cụ còn thiếu
sh bin/studio status       # kiểm tra xưởng (thêm --json cho máy đọc)
```

Sau đó mở Claude Code trong thư mục này và nói điều bạn muốn, ví dụ:

> Làm một phim 40 giây phong cách màu nước về quán cà phê của gia đình tôi.

Gói của thư viện (trình duyệt, Python, giọng đọc, nhạc) được cài khi phim cần: `sh bin/studio deps [voice] [music]`.

## Học phong cách của một kênh

```sh
sh bin/studio deps learn --extra     # công cụ đo + tải video + chép lời (venv riêng tools/.venv)
```

Rồi nói với Claude, ví dụ:

> Học phong cách của kênh https://www.youtube.com/@ten-kenh, 12 video gần nhất.

Claude làm theo skill `.claude/skills/style-learn/`:
1. Tải hoặc nhận video, đo **mọi khung hình** (chuyển động camera, cắt cảnh, màu, độ sáng, âm thanh, tốc độ đọc).
2. Ba agent phân tích song song, rồi kiểm tra chéo với số đo.
3. Viết phong cách 11 mục, mỗi luật có bằng chứng. **Bạn duyệt lần 1.**
4. Vẽ một khung bằng code đặt cạnh khung gốc. **Bạn duyệt lần 2.**
5. Lưu vào `my-styles/<tên>/`, hỏi giữ hay xoá video tham chiếu (mặc định xoá).

Video tham chiếu chỉ để học trên máy: không vào git, không đăng lại. Nếu không tải được (mạng chặn), đặt video vào `references/<tên-bộ>/videos/` rồi dùng `--files`.

Các lệnh lẻ: `sh bin/studio learn fetch | measure | transcribe | summary | check-names | compare | save | clean` (xem `specs/002-style-learning/contracts/learn-cli.md`).

## Cấu trúc

| Đường dẫn | Nội dung | Vào git |
|---|---|---|
| `bin/studio` | Lệnh quản lý xưởng | ✓ |
| `library.lock` | Phiên bản thư viện đã ghim | ✓ |
| `lib/lemo-opuscar/` | Thư viện phong cách (tải bằng `setup`, không sửa) | ✗ |
| `my-styles/` | Phong cách riêng | ✓ |
| `films/` | Phim | ✗ |
| `references/` | Video tham chiếu để học | ✗ |
| `tools/` | Công cụ tự viết (`tools/style-learn/`; venv `tools/.venv` không vào git) | ✓ |
| `specs/` | Spec, plan, tasks của từng tính năng | ✓ |
| `tests/run.sh`, `tests/learn/run.sh` | Test của `bin/studio` và công cụ học phong cách (offline) | ✓ |

## Trạng thái

| # | Tính năng | Trạng thái |
|---|---|---|
| — | Hiến pháp dự án (`.specify/memory/constitution.md`) | v2.0.0 |
| 001 | Khung xưởng phim | Xong |
| 002 | Skill học phong cách từ kênh YouTube | Xong (chờ chạy thật với YouTube trên máy người dùng) |
| 003 | Dùng phong cách riêng như phong cách thư viện | Chưa bắt đầu |

## Nguồn tham khảo
- [github/spec-kit](https://github.com/github/spec-kit): quy trình, template và script (MIT, xem `.specify/LICENSE-spec-kit`).
- [mromidev/claude-animated-shorts](https://github.com/mromidev/claude-animated-shorts): phương pháp đo để học phong cách.
- [lemomo-ai/lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar): thư viện phong cách và công cụ làm phim (MIT; phim mẫu CC BY 4.0).
