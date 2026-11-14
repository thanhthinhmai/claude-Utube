# Quickstart: kiểm chứng 022

## Test tự động

```sh
node --test my-styles/dusk-hypothetical/kit/test/*.test.mjs   # bảng cảnh → SHOTS/CARDS, tên lạ ném lỗi, danh mục khớp module, tư thế ngồi
sh tests/filmcheck/run.sh   # hero của kênh (set, show, attach, ΔE), kit use (chép, cùng băm, khác băm, --update)
sh tests/learn/run.sh       # save bỏ label.log, pipeline.log, review-*.md, .job*; giữ STRUCTURE.md; --update giữ kit/ và demo/
sh tests/run.sh && sh tests/render/run.sh && sh tests/ui/run.sh && sh tests/online/run.sh   # không có gì hỏng
git -C lib/lemo-opuscar status --short   # trống (hiến pháp VI)
```

## Chạy thật

Trước mọi lần dựng: `sh bin/studio status` có dòng `dựng hình: GPU`. Không có GPU thì dừng và hỏi người dùng.

| # | Việc | Kết quả mong đợi | SC |
|---|---|---|---|
| 1 | Chép `kit/catalog.html` thành phim thử `films/kit-catalog/`, `qc shots kit-catalog`; xem bảng ảnh bằng mắt | mỗi bối cảnh: độ sáng 0,22–0,29, bão hoà 0,32–0,41; 0 lỗi phẳng, tối, cháy, mờ; thân tay chân liền, có khớp; tay cầm đúng đồ | SC-001, US1 |
| 2 | Dựng lại bố cục toa tàu bằng kit, chụp `page still`, `learn compare` với khung gốc đã dùng | độ sáng Δ ≤ 0,05, bão hoà Δ ≤ 0,08, vùng rất tối Δ ≤ 5 điểm %, ≥ 4 màu khớp, ngay lần đầu | SC-002 |
| 3 | Cảnh `stadium` 1.000 người, 10 s: `render --fps 60`, đo thời gian | ≤ 3 phút trên GPU; người phân biệt được bằng màu áo, tóc, mũ | SC-003 |
| 4 | Phim mẫu `films/dusk-demo/` theo luồng làm phim (kênh `dusk-hypothetical`, `kit use`), `render --fps 60`, `qc` | mốc màn ±5 điểm % so với `STRUCTURE.md`; cỡ cảnh và góc máy trong khoảng `shots.json`; ≥ 18 bối cảnh; 0 lỗi nặng ở các tầng; `ffprobe` ra 60 fps | SC-004 |
| 5 | Đếm dòng bảng cảnh của `films/dusk-demo/index.html` chia số cảnh; tìm `new THREE.` ngoài `custom` | ≤ 15 dòng mỗi cảnh; không viết lại nhân vật, ánh sáng, hậu kỳ, đồ hoạ | SC-005 |
| 6 | `learn save` trên bộ thử có tệp làm việc | không còn tệp làm việc; `STRUCTURE.md` được lưu | SC-006 |
| 7 | `learn check-names` trên `STRUCTURE.md`, `kit/`, `demo/` | đạt | SC-007 |
| 8 | Chép phim mẫu vào `demo/`, chạy `demo/build.sh` (OUT trong scratchpad) | ra đúng phim của `DEMO.md`, 60 fps; `demo-checks.json` khớp | US4 |

Phải xem bằng mắt bảng ảnh danh mục và ít nhất vài phút phim mẫu (hiến pháp IV).

## Kết quả

(điền khi làm xong)
