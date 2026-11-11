# Tasks: License key và tự cập nhật cho app desktop (017)

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/license-api.md, quickstart.md

## Phase 1: Setup

- [X] T001 `tools/license/requirements.txt` (fastapi, uvicorn, cryptography, argon2-cffi, httpx); thêm `cryptography>=42` vào `tools/requirements-online.txt`; `tests/license/run.sh` (dùng `tools/.venv`, đã có đủ gói)
- [X] T002 [P] `.gitignore`: `deploy/license/.env`, `desktop/build-config.json`, `desktop/updates/`

## Phase 2: Nền tảng (chữ ký dùng chung)

- [X] T003 `tools/license/signing.py`: `new_keypair()`, `sign_lease(priv, payload)`, `verify_lease(pub, lease) → payload|None`, `sign_bytes/verify_bytes` (base64url, R2); `lease_problem(payload, device_id, now, clock)` trả `None` hoặc lý do (`signature`, `device`, `clock`, `expired`, `key_expired`)
- [X] T004 `tools/license/cli.py`: `keygen [--out]`, `admin-password` (hỏi hai lần, ≥ 12 ký tự), `sign-release <tệp>` (contracts)
- [X] T005 [P] `desktop/test/vectors/`: một cặp khoá thử, một lease và một `release.json` cùng chữ ký, do `signing.py` tạo (script `tests/license/make_vectors.py`); test Python kiểm chúng

## Phase 3: User Story 1 + 2 — Key, kích hoạt, khoá (P1) 🎯 MVP

**Mục tiêu**: chủ xưởng cấp và thu hồi key; app mở khi có key hợp lệ, khoá khi mất quyền; phần lõi trả 423.

**Kiểm độc lập**: quickstart §2.

- [X] T006 [US1] `tools/license/store.py`: các bảng của data-model; `create_license`, `list_licenses`, `update_license`, `delete_license`, `remove_device`, `lease_for(key, device…)` → lease hoặc mã từ chối; `in_good_standing(lid, did)`; sessions; events; sao lưu hằng ngày (giữ 30) bằng sqlite backup API
- [X] T007 [US1] `tools/license/server.py`: các route của contracts (lease, releases, health, admin API, `/admin` trả `admin.html`); giới hạn 10 lần mỗi 10 phút theo `X-Real-IP` (sai key, sai mật khẩu); thân tối đa 16 KB; cookie `cu_admin` và `X-CU-Admin`; chạy bằng `python server.py --port`
- [X] T008 [US1] `tools/license/admin.html`: đăng nhập; tạo key (hiện một lần, nút chép); bảng key và máy; sửa, thu hồi hoặc bật lại, xoá; gỡ máy (HTML/JS thuần, chạy được trên màn hình 360 px)
- [X] T009 [US1] `tests/license/test_server.py`: kích hoạt; sai key; hết máy rồi gỡ máy; thu hồi; hết hạn (đồng hồ giả); máy bị gỡ thì bị từ chối, gỡ lần hai thì kích hoạt lại được; key chỉ trả một lần, trong DB chỉ có mã băm (SC-005); lần sai thứ 11 trả 429 (SC-006); admin cần cookie và `X-CU-Admin`; sai mật khẩu bị giới hạn
- [X] T010 [P] [US2] `tools/studio/studio/gate.py`: đọc `STUDIO_LICENSE_GATE` (đọc lại khi mtime đổi), khoá công khai từ `desktop/license-public-key.txt` hoặc `CU_LICENSE_PUBLIC_KEY`; `ok() → (bool, lý do)` theo R4
- [X] T011 [US2] `tools/studio/studio/server.py`: middleware 423 khi có cổng mà cổng đóng (HTML hoặc JSON, trừ `/api/v1/health`); `tools/runner/worker.py`: không lấy việc mới khi cổng đóng; `host.py` và `studio_cli.py`: `app start --gate` lưu vào `host.json`, đặt `STUDIO_LICENSE_GATE` trong `part_env`
- [X] T012 [US2] `tests/online/test_host.py` (lớp `Gate`): cổng tốt thì mở; lease hết hạn, máy khác, đồng hồ lùi, bị từ chối thì trả 423 cho trang và API, `/api/v1/health` vẫn 200; việc trong hàng đợi không chạy khi cổng đóng, chạy khi mở lại (SC-002)
- [X] T013 [US1] `desktop/license.js` (logic thuần): `normalizeKey`, `deviceIdFrom(raw)`, `machineIdCommand(platform)`, `parseMachineId(platform, out)`, `verifyLease(pubB64, lease)`, `leaseProblem(payload, deviceId, nowS, clockS)`, `nextClock`, `classifyResponse(status, body)` (`ok`, `refused`, `offline`), `renewDelayMs(rand)`, `gateFile(state)`, `licenseConfig(buildCfg, env, isPackaged)` (FR-011)
- [X] T014 [US1] `desktop/test/license.test.js`: test cho T013, kể cả kiểm chéo với `vectors/` và sửa một byte thì hỏng
- [X] T015 [US1] `desktop/license.html` và `preload.js`: màn hình nhập key (chế độ `needed`, `locked`), lý do từ chối bằng lời dễ hiểu; `desktop/main.js`: kiểm license trước khi khởi động phần lõi; gia hạn định kỳ; khoá (ẩn cửa sổ, khay "Locked", ghi `gate.json`); nhập key thì mở lại; khay "License…"; lưu key bằng safeStorage (Windows) hoặc Keychain (macOS); `app start --gate`
- [X] T016 [US1] `desktop/test/fake-license.mjs` (máy chủ license giả bằng Node, ký bằng khoá thử) và smoke `--smoke-license` trong `main.js`: nhập key → `window ok` → máy chủ giả chuyển sang thu hồi → `locked ok` → `quit ok`; `.github/workflows/desktop.yml` thêm bước này

## Phase 4: User Story 3 — Tự cập nhật (P2)

**Mục tiêu**: app có key hợp lệ tự nhận bản mới, kiểm chữ ký, cài (Windows) hoặc mở `.dmg` (macOS).

**Kiểm độc lập**: máy chủ license (thật, ở chế độ test) phục vụ một bản phát hành giả; app tải, kiểm, và (Windows) cài khi thoát.

- [X] T017 [US3] `tools/license/server.py` và `store.py`: `/api/license/releases[/{name}]` theo R5 (GitHub API qua `httpx`, lưu đệm 2 phút, danh sách tên cho phép, đọc dạng luồng, cần lease còn tốt lúc này); `LICENSE_GITHUB_API` để test trỏ vào GitHub giả; test trong `tests/license/test_releases.py`
- [X] T018 [US3] `desktop/updates.js` (logic thuần): `newer(a, b)` (semver), `verifyRelease(pub, jsonBytes, sigB64)`, `pickAsset(release, platform)`, `downloadTo(url, headers, file, size, sha256)` (tệp `.part`, kiểm rồi đổi tên), `installCommand(platform, file)`; test trong `desktop/test/updates.test.js` (sửa một byte thì bị từ chối, SC-004)
- [X] T019 [US3] `desktop/main.js`: kiểm bản mới sau 30 giây, rồi mỗi 4 giờ, và khi bấm khay "Check for updates"; Windows: khay "Restart to update", khi thoát thì chạy bộ cài im lặng; macOS: hộp hỏi rồi mở `.dmg`; lúc khởi động, phần lõi khác phiên bản thì hiện bước cài lại phần lõi (016 R7)
- [X] T020 [US3] Smoke cập nhật trên GitHub Actions (`desktop.yml`): máy chủ license giả phục vụ một bản "mới hơn" (bộ cài của chính lần build đó, `release.json` ký bằng khoá thử); app đóng gói tải về và kiểm (`update ready ok`); Windows: chạy bộ cài im lặng và thấy app cài lại (kiểm R6, ghi kết quả vào research)
- [X] T021 [US3] `.github/workflows/desktop-release.yml`: job `installers` ghi `desktop/build-config.json` từ `vars.LICENSE_SERVER_URL`; job `release` tạo `release.json` và `.sig` bằng `secrets.LICENSE_SIGNING_KEY` (thiếu secret mà có biến thì lỗi); đưa cả hai lên Release

## Phase 5: Triển khai và hoàn thiện

- [X] T022 [P] `deploy/license/`: `license.Dockerfile` (python:3.12-slim, người dùng không phải root, chỉ đọc), `compose.yaml` (license và caddy, volume dữ liệu), `Caddyfile` (chỉ `/api/license/*`, `/admin*`, `/health`; đặt `X-Real-IP`; HSTS; bỏ log), `.env.example`, `README.md` (thuê VPS, tên miền, keygen, secret và biến của repo, mã GitHub fine-grained, mật khẩu quản trị, sao lưu khoá ký)
- [X] T023 [P] `tests/license/test_secrets.py`: tìm chuỗi trong repo (`git ls-files`) và trong log thử: không có khoá riêng, key `CU-…` thật hay mã GitHub (SC-005)
- [X] T024 [P] `CLAUDE.md`: mục "License và cập nhật (specs/017)", thêm `tests/license/run.sh` vào danh sách test; `desktop/INSTALL.md`: nhập key, cập nhật
- [X] T025 Chạy đủ các bộ test (5 bộ cũ và `tests/license/run.sh`); đối chiếu FR-001…FR-018, SC-001…SC-006; ghi phần còn kiểm bằng tay vào quickstart

## Dependencies

- Phase 2 (T003) chặn mọi phase sau. T005 cần T003.
- US1/US2: T006 → T007 → T008, T009; T010 → T011 → T012; T013 → T014 → T015 → T016.
- US3 cần T007 (lease) và T015 (app có license). T017 → T018 → T019 → T020; T021 cần T004.

## Parallel

- Máy chủ (T006–T009), cổng của phần lõi (T010–T012) và app (T013–T016) làm song song được sau T003.
- T022, T023, T024 song song.

## Implementation Strategy

MVP = Phase 1–3: có máy chủ license, app hỏi key và khoá được. Rồi US3 (cập nhật). Việc VPS thật (thuê máy, tên miền, secret) do chủ xưởng làm theo README sau khi gộp.
