# claude-Utube

Xưởng phim cho Claude:
- **Học phong cách** của một kênh YouTube bằng cách đo từng khung hình, rồi lưu thành phong cách dùng lại được.
- **Làm phim bằng code** theo phong cách đã học, hoặc theo 66 phong cách có sẵn trong thư viện [lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar).

Dự án được xây theo quy trình [GitHub Spec Kit](https://github.com/github/spec-kit).

## Bắt đầu

Cần: git, Node 20+, ffmpeg 7+, Python 3.11+ (hoặc [uv](https://docs.astral.sh/uv/)); macOS, Linux hoặc WSL.

```sh
git clone https://github.com/thanhthinhmai/claude-Utube.git
cd claude-Utube
sh bin/studio setup        # tải thư viện đúng phiên bản, báo công cụ còn thiếu
sh bin/studio status       # kiểm tra xưởng (thêm --json cho máy đọc)
```

Sau đó mở Claude Code trong thư mục này và nói điều bạn muốn, ví dụ:

> Làm một phim 40 giây phong cách màu nước về quán cà phê của gia đình tôi.

Gói của thư viện (trình duyệt, Python, giọng đọc, nhạc) được cài khi phim cần: `sh bin/studio deps [voice] [music]`.

## Cấu trúc

| Đường dẫn | Nội dung | Vào git |
|---|---|---|
| `bin/studio` | Lệnh quản lý xưởng | ✓ |
| `library.lock` | Phiên bản thư viện đã ghim | ✓ |
| `lib/lemo-opuscar/` | Thư viện phong cách (tải bằng `setup`, không sửa) | ✗ |
| `my-styles/` | Phong cách riêng | ✓ |
| `films/` | Phim | ✗ |
| `references/` | Video tham chiếu để học | ✗ |
| `tools/` | Công cụ tự viết | ✓ |
| `specs/` | Spec, plan, tasks của từng tính năng | ✓ |
| `tests/run.sh` | Test của `bin/studio` (offline) | ✓ |

## Trạng thái

| # | Tính năng | Trạng thái |
|---|---|---|
| — | Hiến pháp dự án (`.specify/memory/constitution.md`) | v2.0.0 |
| 001 | Khung xưởng phim | Xong |
| 002 | Skill học phong cách từ kênh YouTube | Chưa bắt đầu |
| 003 | Dùng phong cách riêng như phong cách thư viện | Chưa bắt đầu |

## Nguồn tham khảo
- [github/spec-kit](https://github.com/github/spec-kit): quy trình, template và script (MIT, xem `.specify/LICENSE-spec-kit`).
- [mromidev/claude-animated-shorts](https://github.com/mromidev/claude-animated-shorts): phương pháp đo để học phong cách.
- [lemomo-ai/lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar): thư viện phong cách và công cụ làm phim (MIT; phim mẫu CC BY 4.0).
