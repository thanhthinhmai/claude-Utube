# Research: Khung xưởng phim

## 1. Bộ máy dựng hình: `render(t)` của lemo-opuscar hay Remotion

- **Decision**: Dùng trang web với hàm `render(t)` của lemo-opuscar, chụp từng khung bằng Chrome chạy ngầm (`core/render/video.mjs`).
- **Rationale**:
  - Thư viện đã có 66 phong cách và toàn bộ công cụ kiểm tra (`readcheck`, `asr_check`, `mux.sh`) viết cho bộ máy này. Hiến pháp VII chỉ cho phép một bộ máy.
  - Bộ máy này dùng JavaScript thuần, ít phụ thuộc, giấy phép MIT.
  - Phương pháp học phong cách (tính năng 002) chỉ cần đầu ra là `STYLE.md` theo khung 11 mục, không phụ thuộc bộ máy.
- **Alternatives considered**:

| Tiêu chí | `render(t)` (lemo-opuscar) | Remotion (claude-animated-shorts) |
|---|---|---|
| Phong cách có sẵn | 66 | 1 |
| Công cụ kiểm tra có sẵn | Đọc chữ, giọng, loudness, cue | QA khung hình (`short_qa.py`) |
| Xem trước | Ảnh tĩnh (`still.mjs`) | Remotion Studio (kéo thanh thời gian) |
| Phụ thuộc | Node, playwright-core, three | React, bundler, `@remotion/*`; khoảng 1,3 GB tạm mỗi lần bundle |
| Giấy phép | MIT | Miễn phí cho cá nhân và công ty tối đa 3 người; lớn hơn phải mua |

  Remotion bị loại cho bộ máy chính. Nếu sau này cần Studio để xem trước, có thể bọc `render(t)` trong một component Remotion; việc đó sẽ là một tính năng riêng, phải giải trình theo hiến pháp VII.

## 2. Ghim phiên bản thư viện

- **Decision**: File `library.lock` ở gốc dự án, dạng `KEY=value`: `LIB_REPO`, `LIB_COMMIT` (SHA 40 ký tự). Phiên bản đầu: `bebbbe1aa92a3cb4bb6f83500e61b23a17d1aa00` (2026-11-01, "Gallery and README: new films for eight styles").
- **Rationale**: SHA không đổi được, khác với tên nhánh. File `KEY=value` đọc được bằng `sh` mà không cần thêm công cụ.
- **Alternatives considered**: git submodule. Bị loại vì người dùng phải nhớ `--recursive`, không hỗ trợ sparse checkout gọn, và dễ bị "sửa" vô tình khi commit.

## 3. Cách tải thư viện

- **Decision**:
  1. Tạo repo tạm `lib/.lemo-opuscar.tmp`, chạy `git init`, thêm remote.
  2. Bật sparse checkout bằng cách ghi thẳng `.git/info/sparse-checkout` (`core.sparseCheckout=true`, `core.sparseCheckoutCone=false`) với cùng mẫu loại trừ như `setup.sh` của thư viện: `/*`, `!/styles/*/demo/`, `!/styleboard/`, `!/docs/frames/`, `!/docs/cover.jpg`, `!/docs/opuscar98.jpg`, `!/styles/*/poster.jpg`. Cách này chạy với mọi bản git ≥ 2.25, không cần `sparse-checkout set --no-cone` (≥ 2.35).
  3. Bật tải từng phần (`remote.origin.promisor`, `partialclonefilter=blob:none`) để chỉ tải file nằm trong phần sparse; máy chủ không hỗ trợ thì tải đủ, kết quả vẫn đúng.
  4. Chạy `git fetch --depth 1 origin <SHA>`, rồi `checkout --detach <SHA>`.
  5. Xong mới đổi tên thành `lib/lemo-opuscar`.

  Nếu máy chủ không cho fetch theo SHA: fetch toàn bộ rồi checkout SHA.
- **Rationale**: Tải vào thư mục tạm rồi đổi tên giúp không bao giờ để lại thư viện dở dang (Edge case "bị ngắt giữa chừng"). Bỏ demo và tải từng phần: đo thật được 17 MB file + 15 MB `.git`, so với 114 MB của bản đầy đủ, mất khoảng 2 giây.
- **Đánh dấu**: `git config studio.managed true` trong repo thư viện. **Không** đặt `lemo.managed`, vì khi có cờ đó, `setup.sh` của thư viện sẽ tự `reset --hard` về `main` và phá phiên bản đã ghim.

## 4. Cài gói của thư viện (`deps`)

- **Decision**: `bin/studio deps [voice] [music]` chạy `LEMO_OPUSCAR_HOME=<gốc>/lib/lemo-opuscar sh lib/lemo-opuscar/plugin/skills/lemo-opuscar/scripts/setup.sh deps …`.
- **Rationale**: Trình cài của thư viện tìm vị trí thư viện theo thứ tự: `$LEMO_OPUSCAR_HOME`, rồi repo git đang đứng, rồi `~/lemo-opuscar`. Chạy từ gốc dự án, nó sẽ thấy repo `claude-utube` (không phải thư viện) và rơi về `~/lemo-opuscar`, tức là tải một bản thư viện thứ hai không ghim. Đặt biến môi trường sẽ chặn được việc này.
- **Hệ quả**: `npm install` có thể ghi lại `package-lock.json` của thư viện. Vì vậy kiểm tra "thư viện bị sửa" bỏ qua đúng file này và ghi điều đó vào báo cáo.

## 5. Kiểm tra công cụ

- **Decision**:

| Công cụ | Lệnh đọc phiên bản | Tối thiểu | Ghi chú |
|---|---|---|---|
| git | `git --version` | 2.25 | |
| Node | `node --version` | 20 | |
| ffmpeg | `ffmpeg -version` dòng 1 | 7 | Bản build ghi theo ngày (`N-…`, `2024-…`) → "không đọc được phiên bản", chỉ cảnh báo |
| Python | `python3 --version` | 3.11 | Đạt nếu có `uv` dù Python thấp hơn (uv tự tải Python) |

- **Rationale**: Theo `TECHNIQUE.md` §1 của thư viện tại commit đã ghim. ffmpeg 6.x báo sai độ dài âm thanh qua `loudnorm` nên phải ≥ 7.
- **So sánh phiên bản**: tách số `MAJOR.MINOR` bằng `sed`, so sánh số nguyên bằng `[ -lt ]`. Không cần `sort -V` (macOS không có).

## 6. Định dạng đầu ra máy đọc được

- **Decision**: `status --json` in một object JSON dựng bằng `printf`, escape `"` và `\` trong chuỗi. Mã thoát: 0 = sẵn sàng, 1 = chưa sẵn sàng, 2 = sai cách dùng.
- **Rationale**: Không phụ thuộc `jq` hay `python`. Hiện các chuỗi trong JSON chỉ là đường dẫn và phiên bản, nên escape đơn giản là đủ.

## 7. Test không cần mạng

- **Decision**: `tests/run.sh` tạo repo git giả làm "thư viện" (có `AGENTS.md`, `core/render/`, `styles/a/STYLE.md`, `styles/_template/STYLE.md`, `styles/a/demo/x.js`), rồi trỏ `STUDIO_LIB_REPO` và `STUDIO_LIB_COMMIT` vào đó. PATH giả chứa script `node`, `ffmpeg`, `python3` in phiên bản mong muốn. `git` thật được giữ trong PATH.
- **Rationale**: Kiểm được mọi nhánh (thiếu, quá cũ, đủ, bị sửa, sai phiên bản, thư mục lạ) trong vài giây và chạy được trong CI. Việc tải thư viện thật từ GitHub được kiểm riêng theo `quickstart.md`.
