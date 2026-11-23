# Implementation Plan: Sửa ghi chú phim After Effects tự động trên app

**Branch**: `031-ae-notes-fix` | **Date**: 2026-11-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/031-ae-notes-fix/spec.md`

## Summary

Đưa bộ dựng AE của phim tập luyện vào `tools/ae/` (bộ dựng chung) với lệnh `sh bin/studio ae build|render|fix|uses <phim>`; mỗi phim AE có `films/<tên>/film.json` (`engine: "ae"`) và `ae/shots_*.jsx`. Vì WSL không gọi ra được Windows nhưng Windows gọi được vào phần lõi, **app desktop kéo việc**: phần lõi giữ hàng đợi "yêu cầu dựng AE"; app desktop (Windows/macOS) hỏi phần lõi bằng một khoá riêng tạo lúc khởi động, tải gói jsx của yêu cầu, chạy After Effects (`AfterFX -r` / `osascript DoScriptFile`) rồi `aerender` từng shot, báo tiến độ, gửi video từng shot về. Trong việc của app, lệnh `ae fix` gửi yêu cầu qua proxy của việc, chờ kết quả, ghép shot vào video theo khung. Thêm loại việc `fix` (nút "Fix with Claude") và tuỳ chọn bộ máy `engine: "ae"` cho việc `film`; khi việc xong, worker thay video và chép trả lời ghi chú vào kho. Luồng GitHub Actions của desktop thêm bài thử cầu nối với AE giả.

## Technical Context

**Language/Version**: Python 3.10+ (phần lõi, worker, proxy, `tools/ae`, `tools/filmcheck`), ExtendScript ES3 (bộ dựng AE, chạy trong After Effects), JavaScript `@ts-check` trên Node 20 / Electron (app desktop), sh.

**Primary Dependencies**: Có sẵn: FastAPI, Claude Agent SDK (agent của việc), Electron, ffmpeg/ffprobe. After Effects 2024+ và `aerender` của người dùng (không đóng gói, hiến pháp VII). Không thêm gói mới.

**Storage**: Hàng đợi AE: `$STUDIO_DATA/ae/requests/<mã>/` (`request.json`, `bundle.tar`, `out/<shot>.mp4`, `log.txt`). Cấu hình AE của máy: `config.json` của app desktop (đường dẫn AE, aerender, thư mục làm việc) và `~/.config/claude-utube/ae.json` cho dòng lệnh khi không có app. Phim AE: `film.json`, `ae/*.jsx`, video và mốc shot như spec 029. Lượt sửa ghi chú: trường `lot` trong `shot-notes.json`.

**Testing**: pytest/unittest trong `tests/ui/` (API cầu nối, hàng đợi, loại việc `fix`, khoá lượt, worker `finished`), `tests/ae/` mới (ghép shot theo khung, `ae uses`, gói jsx, chuyển phim tập luyện so khung), `node --test desktop/test/aebridge.test.js` với AE giả (`desktop/test/fake-ae.mjs`), smoke `ae` trong `desktop.yml`; kiểm tay với AE thật trên Windows và macOS (quickstart).

**Target Platform**: App chế độ "app" (specs/014) trên Windows (lõi trong WSL2) và macOS (lõi chạy thẳng). Chế độ online trên VPS (Docker) không có AE: báo rõ.

**Project Type**: App desktop + web service + CLI có sẵn của xưởng.

**Performance Goals**: Dựng lại 1 shot và ghép ≤ 60 s (SC-001); app desktop nhận yêu cầu trong ≤ 2 s (hỏi mỗi 1 s khi có việc, 5 s khi rảnh); báo thiếu AE ≤ 10 s (SC-004).

**Constraints**: Một lượt AE mỗi lúc (khoá trong app desktop); 5 phút mỗi shot; chỉ app desktop của chính máy gọi được cầu nối (khoá ngẫu nhiên 32 byte + chỉ nhận từ 127.0.0.1); agent chỉ ghi trong thư mục việc (giữ nguyên hook và sandbox hiện có).

**Scale/Scope**: Một máy, một người, phim 20–60 shot; vài lượt sửa mỗi ngày.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá |
|---|---|
| I. Spec là nguồn sự thật | Đạt: spec đã làm rõ 4 câu (2026-11-23). |
| II. Không đoán | Đạt: không còn `[NEEDS CLARIFICATION]`; giả định ghi trong spec. |
| III. MVP theo story | Đạt: US1 (bộ dựng chung, chạy bằng dòng lệnh trên máy) tự chạy; US2 cầu nối; US3 sửa tự động; US4 bộ cài; US5 phim AE mới. |
| IV. Kiểm chứng | Đạt: so khung phim tập luyện (0 khung dưới 30 dB), test với AE giả cho hàng đợi, khoá, thời hạn, quyền; kiểm tay AE thật trên 2 hệ điều hành. |
| V. Đơn giản | Đạt có giải thích: kiểu "kéo việc" qua HTTP là cách đơn giản nhất qua ranh giới WSL→Windows (xem Complexity Tracking). |
| VI. Thư viện gốc | Đạt: không đụng `lib/`. |
| VII. Hai bộ máy, mỗi phim một bộ | Đạt (hiến pháp 3.0.0): `film.json` khai báo bộ máy; lệnh AE từ chối phim web và ngược lại; không cài hay đóng gói AE. |
| VIII, IX | Không áp dụng / đạt (công cụ của xưởng, không spec cho từng phim). |
| Phần mềm hệ thống | Đạt: xưởng không cài AE; app chỉ tìm AE ở chỗ cài mặc định và hỏi đường dẫn. |

Kết quả: **qua cổng**.

## Project Structure

### Documentation (this feature)

```text
specs/031-ae-notes-fix/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/
│   ├── bridge-api.md     # phần lõi ↔ app desktop (kéo việc, tiến độ, kết quả) và proxy ↔ việc
│   ├── cli.md            # sh bin/studio ae … và config ae
│   └── film-ae.md        # film.json, ae/, gói jsx, bộ dựng chung
└── tasks.md
```

### Source Code (repository root)

```text
tools/ae/
├── kit/                 # bộ dựng chung (từ films/ae-crayon-test/ae): lib.jsx, chars.jsx, scene.jsx, persp.jsx, build_core.jsx
├── bundle.py            # gói jsx của một yêu cầu: bộ dựng chung + shot của phim + tệp vào (entry) cho danh sách shot
├── splice.py            # ghép shot vào video theo khung (từ fixshots.sh), cùng mốc shot spec 029
├── uses.py              # shot nào dùng hàm nào của bộ dựng chung (quét tên hàm CU.* trong shots_*.jsx)
├── queue.py             # hàng đợi yêu cầu dựng AE trong $STUDIO_DATA/ae/ (tạo, nhận, tiến độ, kết quả, hết hạn)
├── local.py             # chạy AE trực tiếp từ WSL/macOS khi không có app (dòng lệnh trên máy phát triển)
└── cli.py               # sh bin/studio ae build|render|fix|uses|status, config ae
tools/studio/studio/
├── server.py            # /api/v1/ae/bridge/* (khoá X-CU-Bridge, chỉ 127.0.0.1); /films/{name}/fix (nút); engine trong film_summary
├── jobs.py, quotas.py, api_online.py   # loại việc "fix"; JobIn.engine cho việc "film"
└── web/app.js           # nút "Fix with Claude" (tạo việc, trạng thái lượt), chọn bộ máy ở New film
tools/runner/
├── proxy.py             # /internal/ae/requests… cho việc (gửi gói, chờ, tải kết quả)
├── agent.py             # fix_prompt; film_prompt nhánh engine "ae"
└── worker.py            # prepare: chép phim vào việc fix; finished: thay video + chép trả lời của lượt vào kho
tools/filmcheck/shotnotes.py   # lượt (lot): ghi chú thuộc lượt, khoá lượt, gộp trả lời từ bản trong việc
desktop/
├── aebridge.js          # logic thuần: hỏi việc, khoá một lượt, tìm AE theo hệ điều hành, lệnh AfterFX/osascript/aerender, thời hạn
├── main.js · preload.js · ae.html   # nối cầu, cửa sổ cài đặt After Effects (đường dẫn, thử AE), mục khay "After Effects…"
└── test/aebridge.test.js · test/fake-ae.mjs
.github/workflows/desktop.yml          # smoke: ae (AE giả) trên Windows và macOS
films/ae-crayon-test/                  # (ngoài git) chuyển sang film.json + ae/shots_*.jsx
CLAUDE.md                              # luồng làm phim AE, lệnh ae
```

**Structure Decision**: Bộ dựng AE là công cụ của xưởng (`tools/ae/`), không nằm trong phim. Phần lõi chỉ giữ hàng đợi và cấp gói; mọi việc chạm AE nằm trong app desktop (nơi duy nhất thấy được AE). Việc của app không ghi ra ngoài thư mục việc: worker áp kết quả khi việc xong, như cách chép phim vào kho hiện nay.

## Complexity Tracking

| Phức tạp | Vì sao cần | Cách đơn giản hơn bị loại vì |
|---|---|---|
| Bộ máy dựng thứ hai (After Effects) | Người dùng chốt (hiến pháp 3.0.0): hình từ trang web chưa đạt | Giữ một bộ máy: người dùng đã từ chối |
| Hàng đợi + app desktop kéo việc | WSL2 không gọi được dịch vụ trên Windows (chỉ chiều ngược lại), AE chỉ chạy được trên hệ điều hành của máy | Phần lõi gọi thẳng `.exe` qua WSL interop: không có trong bản Linux đóng gói, không chạy trên macOS, và agent bị sandbox chặn |
| Khoá riêng cho cầu nối | Phần lõi chạy chế độ online: mọi API cần phiên hoặc mã; app desktop không có | Mở route không khoá trên 127.0.0.1: tiến trình bất kỳ trên máy gọi được AE |
