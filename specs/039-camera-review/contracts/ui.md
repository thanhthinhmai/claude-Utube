# UI contract: 039 (trang Camera)

## Vị trí

- Chuỗi điểm duyệt của phim AE: Script → Cast → **Camera** → Voice → Animatic → Mix → Publish.
- Ô chọn điểm duyệt khi tạo việc và ở kênh có thêm "Camera", bật mặc định cho phim AE.
- Phim không có thư viện máy quay: điểm Camera hiện "skipped" kèm lý do.

## Dữ liệu panel (`filmsteps.camera_block`)

```json
{"state": "waiting|approved|must_run_again|skipped", "source": "style:dusk-hypothetical",
 "shots": [{"id": "S3", "dur": 2.8, "chosen": 1, "recommended": 1, "open_notes": 0,
            "options": [{"n": 1, "still": "/films/<f>/file/camera/stills/S3-o1.jpg",
                          "ref": "v03:S041", "ref_frames": ["…a.jpg", "…b.jpg"],
                          "size": "med", "move": "push", "zoom_pct": 5.6, "ease": [0.13,0.48,0.85],
                          "drift_px": [0,8], "start": {"scale":1.12,"cx":46,"cy":44},
                          "transition": "cut", "engine": "ae", "reason": "…", "note": null}]}],
 "missing": ["S7"]}
```

## Hành vi

- **Lưới shot**: mỗi ô là ảnh thử của phương án đang chọn, mã shot và dấu ★ khi đó là phương án khuyên dùng. Ô có ghi chú mở thì có chấm cam.
- **Bấm một shot**: các phương án hiện cạnh nhau, mỗi cột có:
  - ảnh thử với khung zoom cuối;
  - khung a/b của shot mẫu;
  - các số: cỡ, chiều, zoom %, ease, trôi, chuyển cảnh, bộ máy;
  - lý do và cảnh báo (`note`);
  - nút "Use this" và nút ▶ xem trước zoom (CSS transform trong `dur` giây, cubic-bezier theo `ease_ae`).
- **Ghim**: bấm lên ảnh thử để mở ô ghi chú (như Cast/Animatic). "Send notes to Claude" = quyết định revise với note rỗng; server điền `camnotes.summary`.
- **Approve**: bị từ chối khi `missing` không rỗng, hiện danh sách shot.
- Chữ cố định trên giao diện bằng tiếng Anh (quy ước của app).

## API

- Không có route ghi mới: chọn và ghim đi qua `POST /jobs/{id}/actions {point:"camera", op, args, base}` (actions.OPS["camera"]); duyệt và revise đi qua route review có sẵn.
- Ảnh: route tệp phim có sẵn, giới hạn trong `camera/` và `my-styles/<style>/camera/`.
