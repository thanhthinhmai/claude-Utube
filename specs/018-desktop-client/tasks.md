# Tasks: Chế độ Client của app desktop (018)

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/share.md, quickstart.md

## Phase 1: Nền tảng

- [X] T001 `tools/studio/studio/host.py` và `studio_cli.py`: `app cert [--data]` theo contracts (ECDSA P-256, tự ký, 10 năm, quyền 600, dùng lại khi đã có); test trong `tests/online/test_host.py` (lớp `Cert`)
- [X] T002 [P] `desktop/test/vectors/share-cert.json`: một chứng chỉ thử và một chứng chỉ thứ hai (máy giả Host), do `app cert` tạo, ghi rõ chỉ để test

## Phase 2: User Story 1 + 2 — Chia sẻ, ghép đôi, kết nối an toàn (P1) 🎯 MVP

**Kiểm độc lập**: quickstart §2.

- [X] T003 [US1] `desktop/share.js` (logic): `newCode`, `normalizeCode`, `fingerprintOf(derOrPem)`, `proof(code, role, fp, nonceC, nonceH)`, `newToken`, `tokenHash`, `checkClient(share, header)`, `addresses(ifaces, port)` (R6), `Pairing` (mã 10 phút, nonce dùng một lần 2 phút, đếm sai)
- [X] T004 [US1] `desktop/share.js` (cổng): `startGateway({cert, key, port, corePort, state, onChange, updateSource})` → máy chủ HTTPS (R1, contracts): `/__cu/hello`, `pair`, `pair/confirm`, giới hạn sai 10 lần mỗi 10 phút theo địa chỉ, chuyển tiếp có xoá `X-CU-Client`, `stop()` đóng mọi kết nối
- [X] T005 [US1] `desktop/share.js` (phía Client): `pairWithHost(address, code, name)` (R2, kiểm `fp_seen`) → `{fingerprint, hostId, clientId, token}`; `probeHost(address, fingerprint)` dùng cho trang offline
- [X] T006 [US1] `desktop/test/share.test.js`: ghép đôi thành công rồi yêu cầu đi vào phần lõi giả (SSE và tệp lớn); sai mã thì không có token, quá 10 lần thì 429; mã hết hạn sau 10 phút (đồng hồ giả); máy giả Host (chứng chỉ khác) bị phát hiện ở bước 2 và Client không gửi `confirm` (SC-003); không header hoặc token sai thì 403; Client bị gỡ thì 403; bắt luồng byte qua một rơ-le TCP không thấy mật khẩu hay cookie (SC-002); `stop()` thì cổng đóng dưới 2 giây (SC-004)
- [X] T007 [US1] `desktop/main.js`, `preload.js`, `share.html`: khay Host "Share with my team…", cửa sổ chia sẻ (bật/tắt kèm lời nhắc nội bộ, địa chỉ, "Add a computer" hiện mã và đếm ngược, danh sách Client và nút Remove); lấy chứng chỉ bằng `app cert` (qua `coreRun`); bật lại chia sẻ khi mở app nếu lần trước đang bật
- [X] T008 [US1] `desktop/setup.html`, `main.js`, `core.js`: bước chọn chế độ (Host hoặc Client), form Client (địa chỉ, mã, tên máy) gọi `pairWithHost`; `configUsable` cho `mode: "client"`; chế độ Client: không phần lõi, không license, `setCertificateVerifyProc` và `onBeforeSendHeaders` cho Host (R3), cửa sổ chính mở Host, `offline.html` khi mất kết nối, khay rút gọn; thoát không dừng phần lõi nào
- [X] T009 [US1] `desktop/test/fake-host.mjs` (cổng thật + phần lõi giả, in địa chỉ và mã) và smoke `--smoke-client` trong `main.js`: ghép đôi qua `CU_SMOKE_PAIR`, `window ok` (trang của phần lõi giả qua HTTPS đã ghim), Host tắt thì `offline ok`, `quit ok`; thêm vào `.github/workflows/desktop.yml`

## Phase 3: User Story 3 — Cập nhật qua Host (P2)

- [X] T010 [US3] `desktop/share.js`: `/__cu/update[/<tên>]` chuyển tiếp tới máy chủ license bằng lease của Host (R5); Host không có license thì trả 404; test bằng `fake-license.mjs`
- [X] T011 [US3] `desktop/main.js`: Client gọi `checkUpdates` với nguồn là Host (cùng lịch, cùng cách kiểm chữ ký và cài của 017); smoke `--smoke-client` thêm `update ready ok` khi Host giả có bản mới

## Phase 4: Hoàn thiện

- [X] T012 [P] `CLAUDE.md` (mục "Chế độ Client (specs/018)"), `desktop/INSTALL.md` (thành viên nối vào Host; tường lửa; macOS Local Network)
- [X] T013 Chạy đủ 6 bộ test; đối chiếu FR-001…FR-011, SC-001…SC-005; ghi phần còn kiểm bằng tay vào quickstart

## Dependencies

T001 → T007. T003 → T004 → T005 → T006. T007, T008 cần T004, T005. T009 cần T008. T010 cần T004; T011 cần T010, T008.
