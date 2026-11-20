# Quickstart: kiểm bộ dựng Sketch Explainer

Chạy từ gốc dự án (worktree `028-sketch-kit`). Cần `sh bin/studio deps` một lần (thư viện, Chromium).

## 1. Phần thuần và công cụ

```sh
node --test tests/sketchkit/            # lịch hành động, máy, kiểm tên, cỡ cảnh
sh tests/filmcheck/run.sh               # people.py, tầng 1 người thật, quét GPU
sh tests/learn/run.sh                   # soundcraft trong segments
```
Kỳ vọng: đạt hết.

## 2. Phim thử bằng bộ dựng (US1, US2)

```sh
mkdir -p films/kit-try && sh bin/studio kit use kit-try --style sketch-explainer
cp my-styles/sketch-explainer/kit/examples/try.html films/kit-try/index.html   # bảng cảnh mẫu 60 s, chỉ tên trong danh mục
sh bin/studio qc plan kit-try           # tầng 1 đạt, không kit_name
sh bin/studio qc shots kit-try          # tầng 2: không lỗi khung, cách quay trong khoảng shots.json
sh bin/studio render kit-try --fps 30 --skip-checks "kit try"   # bản thử
sh bin/studio learn compare sketch-ref --clip films/kit-try/out/video.mp4   # still_ratio, motion720, moving_share trong khoảng
```
Kỳ vọng: SC-002 đạt; đếm bảng cảnh mẫu 3 phút (`node my-styles/sketch-explainer/kit/tools/count.mjs films/kit-try`) cho 40–55% trung cảnh, ≤ 4 cảnh liền cùng cỡ, 20–28 bối cảnh (SC-003).

## 3. Người thật (US3)

```sh
sh bin/studio people list                       # 7 người đã chuyển từ hai phim cũ: chưa duyệt cho tới khi người dùng duyệt lại bảng mẫu chung (T029)
# thử luồng duyệt bằng một người thử trong thư mục tạm (test_people.py làm tự động); sau khi người dùng duyệt:
sh bin/studio people use kit-try jensen-huang
sh bin/studio qc plan kit-try                   # đạt
# sửa một dòng màu trong people/jensen-huang/figure.js
sh bin/studio people check kit-try              # báo "changed since approval"
sh bin/studio qc plan kit-try                   # chặn: person_unapproved
git checkout people/jensen-huang/figure.js
# thêm bub: [[0, 'We will win', 1]] cho người thật → qc plan chặn: person_words
```

## 4. GPU (US4)

```sh
python3 -m unittest tests/filmcheck/test_sketch_gpu.py   # quét tĩnh + so ảnh danh mục GPU/phần mềm (bỏ qua khi không có GPU)
```

## 5. Phim mẫu (US5)

```sh
OUT=/tmp/sketch-demo sh my-styles/sketch-explainer/demo/build.sh
cat my-styles/sketch-explainer/demo-checks.json   # tầng 1–4 đạt
```

## 6. Đo tiếng động (US6)

```sh
sh bin/studio learn sound sketch-ref --recompute   # dùng số liệu đã lưu; trung vị 12–20/phút (SC-008)
```
