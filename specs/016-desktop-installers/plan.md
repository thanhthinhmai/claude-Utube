# Implementation Plan: Bộ cài app desktop và phần lõi đóng gói sẵn

**Branch**: `016-desktop-installers` | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/016-desktop-installers/spec.md`

## Summary

Hai hệ điều hành dùng cùng một cách: **bộ cài chứa một tệp phần lõi nén**; màn hình thiết lập (015) **cài tệp đó** rồi **tải các mô hình**.

- **Windows** (R1):
  - **Build**: phần lõi là một bản Linux build bằng Docker trên GitHub Actions từ `deploy/core.Dockerfile`: Ubuntu 24.04, gói apt, Node 22, bubblewrap và socat, người dùng `studio` mặc định, studio ở `/home/studio/claude-Utube`, thư viện ở đúng commit của lock, các venv, Chromium của Playwright. Không có mô hình. Lệnh `docker export` cùng gzip cho ra `claude-utube-core-linux-x64-<ver>.tar.gz`.
  - **Cài**: màn hình thiết lập giải nén tệp ra một `.tar` tạm, chạy `wsl --import ClaudeUtube <thư mục> <tar> --version 2`, rồi xoá tệp tạm.
- **macOS** (R2):
  - **Build**: phần lõi build trên máy `macos-14` của GitHub. Python lấy từ python-build-standalone (CPython 3.12, aarch64), và mọi gói Python được cài thẳng vào Python đó (không venv). Thêm Node 22 bản chính thức cho darwin-arm64, ffmpeg và ffprobe bản tĩnh cho arm64, studio, thư viện và Chromium của Playwright. Đóng thành `claude-utube-core-darwin-arm64-<ver>.tar.gz`.
  - **Cài**: màn hình thiết lập giải nén vào `~/Library/Application Support/ClaudeUtube/core-<ver>/`, rồi tạo `tools/.venv` và `lib/lemo-opuscar/.venv` bằng `python -m venv --system-site-packages` (rất nhanh). Phần lõi nằm ở chỗ ghi được, ngoài gói app, nên tải mô hình vào được và chữ ký ad-hoc của app không bị hỏng.
- **Mô hình** (R3): sau khi cài phần lõi, màn hình thiết lập chạy trong phần lõi:
  - `sh lib/lemo-opuscar/tools/fetch.sh voice` (Kokoro; thư viện tự kiểm SHA-256);
  - một lệnh mới `sh bin/studio app models` để tải Whisper `base.en` và `base` vào bộ nhớ đệm của faster-whisper. Bản `small` được tải khi cần, ở lần đầu làm phim tiếng Trung.
- **Bộ cài** (R4): electron-builder, cấu hình ở `desktop/electron-builder.yml`.
  - Windows: NSIS cài cho riêng người dùng, không ký số; trình gỡ hỏi xoá bản Linux và dữ liệu (mặc định giữ).
  - macOS: `.dmg` chip Apple, ký ad-hoc.
  - Tệp phần lõi nằm trong `extraResources/core/`.
- **Sandbox Bash** (R5): `host.part_env` đặt `STUDIO_AGENT_SANDBOX=1` khi có `bwrap` (Linux) hoặc khi chạy trên macOS. `agent.py` khi đó bật `sandbox={"enabled": True, "allowUnsandboxedCommands": False, …}`, cho ghi trong thư mục việc và thư mục tạm, cho mạng tới `127.0.0.1` (proxy). T001 kiểm việc này ngay trong container của phần lõi Linux.
- **Phát hành** (R6): `.github/workflows/desktop-release.yml` chạy khi có tag `desktop-vX.Y.Z` hoặc bấm chạy tay.
  - Job `core-linux`: Docker, export, SHA-256, kiểm container: `app start` → `/api/v1/health` → `app check` → `app stop`, cùng test sandbox.
  - Job `core-mac`: build, kiểm (`app check`, `app start` trên máy macOS).
  - Job `installers`: Windows và macOS, gói tệp phần lõi tương ứng, smoke bộ cài.
  - Job `release`: tạo GitHub Release (riêng tư) với các tệp và `SHA256SUMS`.
- **Cài đè** (FR-012): bộ cài mới thì có tệp phần lõi mới. Màn hình thiết lập so `core-version` đã cài với bản trong bộ cài. Khác nhau thì cài lại phần lõi: Windows sao thư mục dữ liệu ra một tệp tạm trên ổ Windows, rồi `wsl --unregister`, `--import`, và trả dữ liệu về (R7); macOS dùng thư mục `core-<ver>` mới, và dữ liệu vốn nằm ngoài phần lõi.

Chi tiết: [research.md](research.md) · [data-model.md](data-model.md) · [contracts/](contracts/) · [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: Dockerfile, POSIX sh và bash cho script build; JavaScript (Electron, 015) cho bước cài trong app; Python 3.12 cho `app models` và sandbox.

**Primary Dependencies**:
- electron-builder 25.1.8 (ghim bản);
- python-build-standalone (CPython 3.12, aarch64-apple-darwin, bản `install_only`);
- Node 22 bản chính thức;
- ffmpeg và ffprobe bản tĩnh cho macOS arm64 (nguồn chốt ở R2);
- Playwright Chromium; Ubuntu 24.04 (image Docker chính thức).

**Storage**:
- Windows: bản Linux `ClaudeUtube` ở `%LOCALAPPDATA%\ClaudeUtube\wsl\` (tệp vhdx). Dữ liệu của xưởng nằm trong bản Linux (`/home/studio/.local/share/claude-utube`) để chạy nhanh; khi cài lại phần lõi thì dữ liệu được sao ra ngoài rồi trả về (R7).
- macOS: `~/Library/Application Support/ClaudeUtube/core-<ver>/` và thư mục dữ liệu của 014.

**Testing**:
- Test logic Node (`desktop/test`) cho bước cài: dựng lệnh, so phiên bản, kiểm SHA-256, tải tiếp.
- Test Python cho `app models` và cấu hình sandbox.
- Kiểm thật trên GitHub Actions: container phần lõi Linux, phần lõi macOS, smoke bộ cài.
- Bằng tay: SC-001, SC-002, SC-003 trên máy của người dùng.

**Target Platform**: Windows 10 22H2 hoặc 11 bản 64-bit (WSL2); macOS 14 trở lên, chip Apple.

**Project Type**: đóng gói và phát hành, cộng với sửa nhỏ vỏ (015) và phần lõi (014).

**Performance Goals**: tệp phần lõi nén ≤ 1,9 GB (dưới giới hạn 2 GB của GitHub Release và của NSIS); cài xong < 20 phút trên Windows, < 10 phút trên macOS (SC-001, SC-002).

**Constraints**:
- Không cần truy cập repo riêng tư để cài (FR-010). Mô hình tải từ nguồn công khai, có SHA-256.
- Chỉ bật WSL theo hiến pháp 2.2.0. Không cài gói hệ thống nào khác trên máy người dùng: mọi thứ nằm trong bản Linux riêng hoặc trong thư mục của app.

**Scale/Scope**: một bản phát hành gồm 2 bộ cài và 2 tệp phần lõi.

## Constitution Check

| Nguyên tắc | Kết quả |
|---|---|
| I. Spec là nguồn sự thật | ✓ Đã làm rõ 3 câu |
| II. Không đoán | ✓ có điều kiện. Ba điều chưa thử, T001 kiểm và dừng hỏi nếu khác: (a) `wsl --import` và dung lượng tệp phần lõi thật sau khi nén; (b) sandbox Bash của Claude Code trong container Ubuntu có bubblewrap, có cho gọi proxy `127.0.0.1` không; (c) ffmpeg tĩnh cho macOS arm64 từ nguồn chọn ở R2 chạy được và có giấy phép phát lại rõ |
| III. MVP theo story | ✓ US1 (Windows) tự đứng được: tệp phần lõi Linux cùng bộ cài Windows. US2 (macOS), US3 (phát hành tự động) thêm sau |
| IV. Đo được | ✓ Dung lượng, thời gian, `CREDITS` (SC-005), sandbox (SC-006) có kiểm tự động trên Actions. SC-001 … SC-003 bằng tay |
| V. Đơn giản | ✓ Hai hệ điều hành dùng cùng mẫu "tệp phần lõi trong bộ cài, cài lúc thiết lập". Dùng lại lệnh tải mô hình của thư viện. Một mục ở Complexity Tracking |
| VI. Thư viện gốc | ✓ Thư viện được clone ở đúng commit của lock, không sửa. Kèm tệp LICENSE (MIT) |
| VII–IX | ✓ Không đổi |
| Phần mềm hệ thống (2.2.0) | ✓ Chỉ bật WSL khi người dùng bấm và đồng ý. Gói apt chỉ cài **trong bản Linux riêng của app** lúc build, không cài trên máy người dùng |
| Bản quyền, nội dung | ✓ Mọi phần mềm và mô hình ghi vào `CREDITS` kèm giấy phép (FR-004, SC-005 có kiểm tự động). ffmpeg: chọn bản có giấy phép phát lại rõ (R2) |

Kiểm lại sau thiết kế: đạt, với điều kiện T001.

## Project Structure

### Documentation (this feature)

```text
specs/016-desktop-installers/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/
│   └── release.md    # tên tệp phát hành, core-manifest.json, các bước cài trong app, app models
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
deploy/core.Dockerfile                 # mới: phần lõi Linux (Windows)
desktop/core-build/
├── build-linux.sh                     # mới: docker build → export → tar.gz → SHA-256 → core-manifest.json
├── build-mac.sh                       # mới: python-build-standalone + gói + node + ffmpeg + studio + lib + Chromium → tar.gz
├── smoke-core.sh                      # mới: kiểm một phần lõi đã build (app check, start, health, stop, sandbox)
└── credits-check.py                   # mới: danh sách phần mềm trong phần lõi so với CREDITS (SC-005)
desktop/electron-builder.yml           # mới: NSIS (per-user) và dmg (arm64, ad-hoc); extraResources core/
desktop/installer.nsh                  # mới: trình gỡ hỏi xoá bản Linux và dữ liệu
desktop/core.js · main.js · setup.html # sửa: bước cài phần lõi và tải mô hình (FR-008), so phiên bản (FR-012)
desktop/package.json                   # sửa: electron-builder, scripts pack
tools/studio/studio/host.py · studio_cli.py   # sửa: app models; STUDIO_AGENT_SANDBOX khi có sandbox
tools/runner/agent.py                  # sửa: sandbox theo STUDIO_AGENT_SANDBOX
.github/workflows/desktop-release.yml  # mới: core-linux, core-mac, installers, release
.github/workflows/desktop.yml          # sửa: actions v5
CREDITS                                # sửa: mọi phần mềm và mô hình đi kèm
```

## Complexity Tracking

| Vi phạm | Vì sao cần | Cách đơn giản hơn bị loại vì |
|---|---|---|
| Hai cách build phần lõi riêng (Docker cho Linux, script cho macOS) | macOS không chạy được bản Linux; phần lõi phải chạy thẳng trên máy Mac | Bắt người dùng Mac cài Docker hay Homebrew thì trái hướng "một tệp cài" và trái luật phần mềm hệ thống. Dùng máy ảo Linux trên Mac thì nặng hơn nhiều |
