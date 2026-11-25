# Quickstart: kiểm chứng tính năng cast

## Điều kiện

- After Effects đã cấu hình (`sh bin/studio ae status` báo sẵn sàng) hoặc app desktop đang chạy với cầu nối AE sẵn sàng.
- Phim thử `films/ae-sleepless-test` (3 nhân vật: hero, friend, classmates).

## 1. Test tự động (không cần AE)

```sh
sh tests/filmcheck/run.sh test_cast test_castnotes test_castlib test_points test_steps test_edit
sh tests/ae/run.sh          # có test_rigs (bất biến rigs.lock), test_sheet (tách khung từ video giả)
sh tests/ui/run.sh          # có test_cast_api, browser_cast.cjs (ghim lệch ≤ 2%, xoá ghi chú, Request/Undo)
sh tests/online/run.sh      # có test_cast_fix_job (việc fix target cast với agent giả)
sh tests/run.sh
```

Kỳ vọng: tất cả đạt; cổng: `voice make` trên phim AE có nhân vật chưa duyệt trả mã 1 kèm tên nhân vật (SC-002).

## 2. Bảng mẫu thật (US1)

```sh
sh bin/studio cast check ae-sleepless-test        # 0
sh bin/studio ae sheet ae-sleepless-test           # ≤ 5 phút (SC-001)
sh bin/studio cast status ae-sleepless-test        # 3 dòng "ready"; point cast: waiting
sh bin/studio voice make ae-sleepless-test         # mã 1: characters not approved: hero, friend, classmates
```

Mở `films/ae-sleepless-test/cast/sheets/hero/`: có `front.jpg`, `back.jpg`, `34.jpg`, các `expr-*.jpg` và `pose-*.jpg` đúng `needs`, `walk.mp4`. Xem bằng mắt: đầu cầu bóng, mắt có con ngươi, mũ không che mắt.

## 3. Ghi chú và vẽ lại một nhân vật (US2, SC-003)

Trên trang việc (app) hoặc bằng lệnh:

```sh
sh bin/studio cast notes show ae-sleepless-test    # base: …
# thêm 1 ghi chú có ghim trên friend/front qua trang việc, rồi "Send notes to Claude"
```

Kỳ vọng sau lượt vẽ lại: chỉ `cast/sheets/friend/` đổi (có `friend.prev/`); ảnh của `hero` và `classmates` giống hệt trước (so sha256); ghi chú có `reply`; `friend` về `ready`.

## 4. Duyệt và kho (US3, SC-005)

```sh
sh bin/studio cast approve ae-sleepless-test --all --save    # app đang chạy
sh bin/studio cast library default                            # hero, friend, classmates v1
sh bin/studio ae new ae-cast-reuse && sh bin/studio cast use ae-cast-reuse default/hero
sh bin/studio cast status ae-cast-reuse                       # hero: approved (library v1)
```

Dựng `ae sheet ae-cast-reuse`: `front.jpg` của hero giống hệt bản trong kho (so điểm ảnh).

## 5. Phiên bản rig (US4, SC-006)

```sh
sh bin/studio ae rigs --check                                 # 0
# tạo tools/ae/kit/rigs/ball/v2/ (thêm góc), rồi:
sh bin/studio ae rigs --lock ball@2
sh bin/studio cast library default                            # hero: new rig version
sh bin/studio ae build ae-sleepless-test --shots S2           # khung giống hệt trước (hero vẫn ball@1)
```

Sửa một tệp trong `v1/` rồi chạy `ae rigs --check`: mã 1.
