# Research: 040-whatif-rig

## R1. Tỉ lệ nhân vật mẫu (đo)
- **Decision**: lấy số trong `references/whatif-long/analysis/rig-measure.json` (20 nhân vật, 15 khung, 7 video, chính xác ≈ ±0,02 W). Đầu là hình tròn R=200 px trong khung người 1000×1400 (W=400). `kid`/`adult` cao 3,15 đầu (1260 px, đúng chiều cao khung từ đỉnh đầu y=100 tới chân y=1360). `toddler` 2,14 đầu (856 px): đầu tâm y≈704.
- Tay 0,20 W = 80 px, chân 0,22 W = 88 px, bàn tay 0,23 W ≈ 92 px, mắt 0,24 W ≈ 96 px, giày 0,36×0,21 W = 144×84 px. Thân `kid` rộng 0,56 W = 224 px, cao 0,98 W = 392; `adult` 0,67 W = 268 px, 1,08 W = 432. `toddler` thân 0,5 W, chân 0,65 W.
- Viền ≈ 1,5 px ở 720p. Người trong cảnh thường cao ≈ 250–450 px ở 720p, tức khung 1400 px được thu ≈ 0,2–0,35: viền trong khung người ≈ 6 px (1,5 px / 0,25). Chọn 6 px, chồng lên thân 10 px.
- **Rationale**: báo cáo phân tích cũ ghi 3–3,5/4,5 đầu không khớp số đo; nguyên tắc VIII yêu cầu đo trên ≥ 10 khung.
- **Alternatives**: giữ tỉ lệ `ball@2` (2,74 đầu, chân 0,09 W): bị loại, là nguồn lệch chất.

## R2. Vẽ "khối" trong AE 2D
- **Decision**: mỗi đoạn tay, chân = 3 nét trên cùng một đường (biểu thức như `ballLimbPath` nhưng đường gấp khúc A → khớp → B, không cong): nét viền tối (sw+12), nét màu (sw), nét dải tối (≈ 0,28 sw) dời sang phía phải màn hình theo pháp tuyến. Đầu nét tròn, nối tròn: khuỷu thành hai ống chồng góc như mẫu. Thân: hình có nét viền 6 px, gradient bằng lớp ramp nhân (multiply) cắt theo thân (`preserveTransparency`), như lớp "grade" của `ball@2`.
- Đầu: không viền tối; gradient trên sáng/dưới tối (lớp tô mờ như `ball@2`), điểm sáng trên phải, viền sáng mảnh dày hơn ở phải (hai elip lệch tâm).
- **Alternatives**: Blender toon cho nhân vật: loại theo quyết định 038 (một bản code AE).

## R3. Kích thước theo tuổi trong bảng mẫu
- **Decision**: `rig.size` giữ số của `kid` (headY 300, R 200, fx 500, fy 1360) để toàn thân của `toddler` tự nhỏ hơn đúng tỉ lệ; thêm `rig.sizeOf(spec)` trả headY theo tuổi; `castsheet.jsx` dùng nó cho ảnh cận mặt nếu có (rig cũ không có hàm này → giữ như cũ).

## R4. Bối cảnh bếp và phòng khách
- **Decision**: viết theo khuôn `office.py` (hộp, cầu, ống của `mesh`, `toon.mat`, viền `outline`, lớp fg/mid/bg/far, `lights.preset` + đèn vùng, `k.objects` có `look`, `cam_dir`, `floor`, `walk`). Màu lấy từ khung mẫu (tủ xanh xám, mặt đá gỗ nhạt, tường kem có ván, giấy dán tường hoạ tiết nhỏ cho phòng khách, cửa sổ có cảnh ngoài).
- Kiểm độ sáng/tương phản/bão hoà bằng cùng công thức của `learn measure` (`tools/style-learn`) trên ảnh ¼ cỡ; chỉnh `exposure` như `office.py` nếu lệch.

## R5. Khoá phiên bản
- `ball@3` vào `rigs.lock` thì thành bản mới nhất của họ `ball`: nhân vật cũ thấy "rig có bản mới" ở trang Cast (luồng sẵn có, không tự đổi). Bundle mang thêm `ball@3`. Chấp nhận (đúng thiết kế 034).
- Khoá sau khi bảng mẫu được duyệt; trước đó test chạy với thư mục chưa khoá qua `rigs.check` không bị ảnh hưởng (chỉ id trong khoá được kiểm).
