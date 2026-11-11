# Implementation Plan: License key và tự cập nhật cho app desktop

**Branch**: `017-desktop-license-updates` | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)

## Summary

Ba phần, đi theo cách neb-creative-tool làm (research R1), có sửa những chỗ neb tự nhận còn yếu:

1. **Máy chủ license** (`tools/license/`, Python, FastAPI, SQLite):
   - cấp key, quản lý máy, ký giấy phép ngắn hạn (lease) bằng Ed25519;
   - chuyển tiếp các tệp của bản phát hành riêng tư cho người có lease còn tốt;
   - có trang quản lý đăng nhập bằng mật khẩu của chủ xưởng.

   Triển khai bằng `deploy/license/` (Caddy và một container Python; tự sao lưu SQLite hằng ngày).
2. **App desktop**:
   - `desktop/license.js` (logic thuần): chuẩn hoá key, mã máy, kiểm lease, chống lùi đồng hồ;
   - `desktop/license.html`: màn hình nhập key và màn hình khoá;
   - `desktop/updates.js`: kiểm, tải, kiểm chữ ký và SHA-256 bản mới.

   Cách cài bản mới:
   - Windows: chạy bộ cài NSIS ở chế độ im lặng khi thoát app;
   - macOS: mở `.dmg`.

   App ghi một **tệp cổng** (gate) cho phần lõi.
3. **Phần lõi**:
   - `app start --gate <tệp>` truyền đường dẫn tệp cổng tới web và worker;
   - web kiểm lại lease trong tệp cổng ở mọi lời gọi, sai thì trả 423;
   - worker không nhận việc mới khi tệp cổng không còn tốt, nhưng việc đang chạy vẫn làm xong.

Workflow phát hành (016) thêm `release.json` (phiên bản, tên, kích thước, SHA-256 của từng tệp) và `release.json.sig`, ký bằng cùng khoá Ed25519 (secret `LICENSE_SIGNING_KEY`). Bản build chỉ có license khi có biến repo `LICENSE_SERVER_URL` và tệp khoá công khai `desktop/license-public-key.txt` (FR-011).

Chi tiết: [research.md](research.md) · [data-model.md](data-model.md) · [contracts/](contracts/) · [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**:
- Python 3.12 cho máy chủ license và tệp cổng của phần lõi;
- JavaScript (Electron 33, Node 20 có sẵn `fetch` và Ed25519 trong `node:crypto`) cho app.

**Primary Dependencies**:
- máy chủ license: `fastapi`, `uvicorn`, `cryptography`, `argon2-cffi`, `httpx`;
- phần lõi: thêm `cryptography` vào `tools/requirements-online.txt` (hiện có sẵn gián tiếp);
- app: không thêm gói nào (bỏ electron-updater, R6).

**Storage**:
- máy chủ license: SQLite ở `$LICENSE_DATA/license.db`, sao lưu mỗi ngày vào `backup/` (giữ 30 bản);
- app: `config.json` (lease, mốc giờ, trạng thái từ chối), key trong kho bí mật của hệ điều hành, bản mới trong `<userData>/updates/`.

**Testing**:
- `tests/license/` (unittest, mới, có `run.sh`): API, giới hạn, trang quản lý, chuyển tiếp bản phát hành với GitHub giả;
- `desktop/test/license.test.js`, `desktop/test/updates.test.js`: kiểm lease với cặp khoá thử, cùng tệp mẫu do Python ký (kiểm chéo hai ngôn ngữ);
- `tests/online/test_host.py`: tệp cổng (423, worker không nhận việc);
- smoke Electron: một máy chủ license giả bằng Node.

**Target Platform**:
- máy chủ license: Ubuntu VPS nhỏ có Docker và tên miền;
- app: như 016.

**Performance Goals**: gia hạn mỗi 15 phút (±2 phút ngẫu nhiên), kiểm bản mới mỗi 4 giờ; khoá trong ≤ 15 phút khi có mạng (SC-002).

**Constraints**:
- Khoá ký, mã GitHub, mật khẩu quản trị chỉ nằm trên VPS hoặc trong secret của repo (SC-005).
- Không thêm phần mềm hệ thống trên máy người dùng.

**Scale/Scope**: vài chục key và máy; một tiến trình.

## Constitution Check

| Nguyên tắc | Kết quả |
|---|---|
| I. Spec là nguồn sự thật | ✓ 3 câu đã chốt |
| II. Không đoán | ✓ Cách làm có thật ở neb (R1). Điều chưa thử: NSIS chạy im lặng `/S --force-run` khi app đang thoát. Kiểm trên GitHub Windows ở T020 |
| III. MVP theo story | ✓ US1 + US2 (license và khoá) tự đứng được; US3 (cập nhật) thêm sau |
| IV. Đo được | ✓ SC-002, 004, 005, 006 kiểm tự động; SC-001, 003 bằng tay |
| V. Đơn giản | ✓ Một tiến trình, SQLite, không Postgres. Bỏ electron-updater: chạy bộ cài im lặng là đủ. Lease và chữ ký bản phát hành dùng chung một khoá |
| VI. Thư viện gốc | ✓ Không đụng `lib/` |
| Bản quyền, nội dung | ✓ Không có tài sản mới. `CREDITS` không đổi (không thêm gói vào bộ cài ngoài `cryptography`, đã có sẵn) |
| Không commit secret | ✓ Chỉ khoá **công khai** vào repo; khoá riêng và mã GitHub ở secret và `.env` của VPS. SC-005 có test tìm chuỗi |
| Phần mềm hệ thống | ✓ Không cài gì trên máy người dùng. VPS do chủ xưởng tự lo (hướng dẫn trong `deploy/license/README.md`) |

## Project Structure

### Documentation

```text
specs/017-desktop-license-updates/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md · tasks.md
├── contracts/license-api.md   # API của máy chủ license, lease, release.json, tệp cổng
└── checklists/requirements.md
```

### Source Code

```text
tools/license/
├── server.py          # FastAPI: /api/license/lease, /api/license/releases[/<tên>], /admin, /health
├── store.py           # SQLite: licenses, devices, admin, sessions, events; sao lưu hằng ngày
├── signing.py         # Ed25519: ký và kiểm lease, release.json; dùng chung với phần lõi
├── cli.py             # keygen, admin-password, sign-release
├── admin.html         # trang quản lý (HTML/JS thuần)
└── requirements.txt
tools/studio/studio/gate.py     # phần lõi: đọc tệp cổng, kiểm lease (dùng signing.verify)
tools/studio/studio/server.py   # middleware 423
tools/studio/studio/host.py · studio_cli.py   # app start --gate
tools/runner/worker.py          # không nhận việc mới khi cổng đóng
desktop/license.js · license.html · updates.js · main.js · preload.js · core.js
desktop/license-public-key.txt  # khoá công khai (chủ xưởng ghi sau keygen; rỗng = không có license)
desktop/test/license.test.js · updates.test.js · fake-license.mjs · vectors/
deploy/license/        # license.Dockerfile, compose.yaml, Caddyfile, .env.example, README.md
.github/workflows/desktop-release.yml   # release.json + chữ ký, cấu hình license lúc build
tests/license/         # run.sh + test_*.py
```

## Complexity Tracking

| Vi phạm | Vì sao cần | Cách đơn giản hơn bị loại vì |
|---|---|---|
| Thêm một dịch vụ chạy riêng (máy chủ license) | App chạy trên máy người dùng, nên phải có nơi ngoài máy họ để cấp và thu hồi quyền | Key ký sẵn, không có máy chủ, thì không thu hồi được (trái US2) và không chuyển tiếp được bản phát hành riêng tư |
