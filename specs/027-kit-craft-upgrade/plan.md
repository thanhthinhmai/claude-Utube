# Implementation Plan: Nâng tay nghề bộ dựng 3D

**Branch**: `027-kit-craft-upgrade` | **Date**: 2026-11-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/027-kit-craft-upgrade/spec.md`

## Summary

Bộ dựng 023 đã khớp các số trung bình và chuyển động máy của kênh mẫu, nhưng trong khung **nhân vật ít làm việc**, bối cảnh tối và trống. Tính năng này làm năm việc, theo thứ tự ưu tiên của spec:

1. **Đo tay nghề của kênh mẫu** (nền cho FR-014): module mới `tools/filmcheck/craftlabel.py` gán ba nhãn (có hành động thật, ngoài trời, có đồ trong tay) cho cả 2.192 cảnh của `references/dusk-hypothetical-3`, bằng một `claude -p` độc lập (Opus 5.5, như `labeler.py`), trên các bảng ảnh cảnh đã có. Lệnh `learn craft-label <set>`. Tỉ lệ được ghi vào `template.json → craft`. Qua vai lấy từ nhãn góc đã có.
2. **Diễn xuất và góc máy** (US1):
   - `figure.js` thêm đồ cầm tay (bóng, bài, tiền, hộp, chìa khoá) có điểm bám từng tay, và tư thế chân mới (chạy, nhảy, ngã, bê).
   - `acting.js` thêm các động tác cả người và hai người dưới dạng hàm thuần theo thời gian, nên vẫn tất định và test được bằng `node --test`.
   - `plan.js` tự chọn máy qua vai cho cảnh hai người có `talk` mà không ghi `cam`, đổi phía theo luật 180°.
   - `camera.js` thêm máy `hands` (cận tay cầm đồ) và `hero-low` (góc thấp).
3. **Bối cảnh** (US2): `sets/parts.js` thêm các phần dùng chung (cây, cột đèn, hàng rào, nhà có cửa sổ sáng, rổ bóng, lan can sân thượng, vạch bãi xe, vòm trời). Thêm 4 bối cảnh `court`, `rooftop`, `parking`, `street-dusk`. Mỗi bối cảnh khai báo `outdoor`, `props` theo lớp và `props_min`.
4. **Ánh sáng và hậu kỳ** (US3): đưa bản thử v2 (`films/kit-post/kit/stage.js`) vào `stage.js` thành mặc định mới (vòm trời, sương sáng, AO, phơi sáng, độ bão hoà, ánh mặt), thêm `windowGlow` và vệt nắng cho bối cảnh trong nhà. Chỉnh số bằng `learn compare`; nếu khoảng của phong cách mâu thuẫn với bảng ảnh kênh mẫu thì đo lại và ghi vào `EVIDENCE.md` (R8).
5. **Kiểm và chứng minh** (US1, US2, US4):
   - Trang phim xuất thêm `window.CRAFT`, mỗi cảnh một dòng gồm có hành động, ngoài trời, đồ trong tay, góc máy.
   - `plan.mjs` đọc nó; module mới `craftcheck.py`, gọi từ `plancheck.py`, áp các luật của `template.json → craft`.
   - Mỗi nhóm thành phần có trang thử, bảng so ba hàng (ô kênh mẫu cùng loại, trước, sau) và clip ≤ 10 s, được người dùng duyệt trước khi sang nhóm sau.
   - Cuối cùng làm lại phút đầu của pause-ten-seconds trong `films/pause-ten-redo`.

## Technical Context

**Language/Version**: JavaScript ES module thuần cho kit (chạy trong trang của thư viện); Python 3 (chỉ thư viện chuẩn) cho `tools/filmcheck` và `tools/style-learn`.

**Primary Dependencies**: three.js và `core/three/post.js` của thư viện (GTAO, DOF, bloom có sẵn: chỉ bật và chỉnh qua tham số `makePost`); `claude -p` với model của xưởng (`tools/models.json`, Opus 5.5) cho lượt gán nhãn; ffmpeg cho bảng so và clip (bản ở đây không có `drawtext`: nhãn hàng ghi bằng ảnh nhãn tạo sẵn hoặc trong trang HTML).

**Storage**: tệp. Nhãn tay nghề lưu ở `references/dusk-hypothetical-3/profile/craft-labels.json` (không vào git), có cache theo phiên bản prompt. Tỉ lệ ghi vào `my-styles/dusk-hypothetical/template.json`, bằng chứng vào `EVIDENCE.md`.

**Testing**: `node --test my-styles/dusk-hypothetical/kit/test/*.test.mjs` (đồ bám tay, động tác, chọn máy qua vai, đếm đồ bối cảnh, tất định); `sh tests/filmcheck/run.sh` (craftcheck, plancheck có CRAFT); `sh tests/learn/run.sh` (craftlabel với `claude` giả); xem thật bằng bảng so và clip.

**Target Platform**: Linux/WSL2 của xưởng, dựng bằng GPU (Chrome đầy đủ trên WSLg).

**Project Type**: bộ dựng phim (thư viện JS trong phong cách) cùng công cụ CLI kiểm và học.

**Performance Goals**: dựng một phút phim bằng GPU tăng ≤ 50% so với kit 023 (SC-006). Riêng AO được đo trước khi bật mặc định (R4).

**Constraints**: không sửa `lib/` (hiến pháp VI); `render(t)` tất định; bảng cảnh cũ chạy không đổi; phim cũ giữ kit đã chép (FR-013); mọi số có bằng chứng hoặc nhãn "xưởng" (hiến pháp VIII). Làm trong worktree `../claude-Utube-027` vì thư mục chính đang có phiên khác làm spec 026; `lib/`, `references/`, `films/`, `tools/.venv` không có trong git nên được nối (symlink) sang thư mục chính, và không commit các liên kết đó.

**Scale/Scope**: 2.192 cảnh mẫu được gán nhãn (khoảng 20 lượt gọi); thêm 5 đồ, 9 động tác, 2 máy, 4 bối cảnh, 10 phần dựng; phút làm lại khoảng 18 cảnh.

## Constitution Check

| Nguyên tắc | Đánh giá |
|---|---|
| I. Spec là nguồn sự thật | Đạt: plan theo spec 027 đã clarify. |
| II. Không đoán | Đạt: ngưỡng tay nghề đo từ kênh mẫu (Clarification A). Mức 50% ghi nhãn "luật xưởng tạm". |
| III. MVP trước, chia theo story | Đạt: thứ tự đo → US1 → US2 → US3 → US4, mỗi nhóm có bảng so được duyệt trước khi sang nhóm sau. |
| IV. Đo được | Đạt: test cho logic thuần; bảng so, clip, `learn compare`, tầng 0–4 cho hình. |
| V. Đơn giản | Đạt: mở rộng các module có sẵn; chỉ thêm hai module Python nhỏ. |
| VI. Thư viện giữ nguyên | Đạt: chỉ dùng `post.js` qua tham số. |
| VII. Một bộ máy dựng hình | Đạt: vẫn three.js, không thêm SVG. |
| VIII. Học bằng đo | Đạt: lượt gán nhãn mới, tỉ lệ kèm nguồn; số màu kiểm bằng `learn compare`, đo lại nếu mâu thuẫn. |
| IX. Spec-kit cho phần mềm | Đạt: phút làm lại là phép thử của bộ dựng, đi theo luồng làm phim. |
| Bản quyền | Đạt: đồ, bối cảnh, động tác tự dựng; bảng so dùng ô kênh mẫu chỉ nội bộ, không commit ảnh kênh mẫu. |

Sau Phase 1: không đổi, không có vi phạm.

## Project Structure

### Documentation (this feature)

```text
specs/027-kit-craft-upgrade/
├── plan.md, research.md (R1–R8), data-model.md, quickstart.md
├── contracts/kit-api-v3.md, contracts/cli.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
my-styles/dusk-hypothetical/
├── kit/
│   ├── figure.js        # 5 đồ mới, điểm bám tay, chân run/jump/fall/carry
│   ├── acting.js        # act cả người và hai người (hàm thuần), handoff, đường ném
│   ├── plan.js          # kind của act, mặc định qua vai + 180°, CRAFT, kiểm tên mới
│   ├── camera.js        # máy hands, hero-low
│   ├── stage.js         # grade v3 (từ v2), AO, vòm trời, sương sáng
│   ├── film.js          # đồ chuyển tay, đồ bay, xuất window.CRAFT
│   ├── catalog.json     # items, acts {kind}, cams, sets {outdoor, props_min}
│   ├── GRADE.md         # số mới kèm bằng chứng
│   ├── sets/parts.js    # tree, streetLamp, fence, house, hoop, railing, parkLines, skyDome, windowGlow, sunBeam
│   ├── sets/court.js, rooftop.js, parking.js, street-dusk.js   # mới
│   ├── sets/(7 bối cảnh cũ)   # thêm đồ cho đủ props_min, cửa sổ sáng
│   └── test/items.test.mjs, acting-v3.test.mjs, ots.test.mjs, sets.test.mjs
├── template.json        # + craft
├── EVIDENCE.md          # + bằng chứng craft (và khoảng màu nếu đo lại)
└── TEMPLATE.md          # + cách dùng act, đồ, bối cảnh, máy mới

tools/filmcheck/craftlabel.py, craftcheck.py (mới); plancheck.py, plan.mjs (sửa)
tools/style-learn/learn.py   # lệnh craft-label
tests/filmcheck/test_craft.py, tests/learn/test_craftlabel.py
```

**Structure Decision**: mở rộng tại chỗ bộ dựng của phong cách và `tools/filmcheck`. Không thêm module chung nào khác.

## Complexity Tracking

Không có vi phạm hiến pháp cần giải thích.
