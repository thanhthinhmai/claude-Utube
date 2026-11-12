# Research: Học cách quay của kênh tham chiếu (021)

Mỗi mục: **Quyết định**, **Lý do**, **Đã cân nhắc**.

## R1. Một phép đo độ nét cho video tham chiếu và cho phim (FR-003, FR-011)

**Quyết định**: viết module mới `tools/filmcheck/focus.py`, chỉ dùng thư viện chuẩn của Python và ffmpeg. Với một ảnh khung (JPEG, 960×540):
- ffmpeg thu ảnh về 480 px chiều ngang, xám, rồi xuất điểm ảnh thô;
- bỏ dải đen trên dưới (các hàng có độ sáng < 0,03 và độ lệch < 0,01, tính từ mép vào) và dải phụ đề (18% dưới của phần hình, tham số);
- chia phần còn lại thành 4×3 ô, tính phương sai Laplace của từng ô;
- một ô "nét" khi phương sai ≥ `FOCUS_T`.

Kết quả gồm: phương sai từng ô, `focused_share` (số ô nét / 12), ô nét nhất và vị trí của nó. Style-learn (gọi từ `tools/.venv`) và `qc shots` dùng đúng module này trên ảnh cùng cỡ 960×540.

**Ngưỡng**: thử ban đầu với `FOCUS_T = 40`. Trên số đo ngày 2026-11-12, ngưỡng này cho khung mẫu của phong cách 12/12 ô nét và `pet-swap` 128/192 khung không ô nào nét. Ngưỡng được chốt lại trên khung giữa cảnh của video tham chiếu khi học lại (T-task): ít nhất 95% khung tham chiếu có ít nhất một ô nét. Con số cuối cùng ghi vào research này và vào `focus.py`.

**Lý do**: FR-003 đòi cách đo giống hệt ở hai phía. Tầng 2 hiện đo trong trang bằng JS, còn style-learn đo bằng numpy, nên hai bên dễ lệch nhau. Một module Python duy nhất, chạy trên cùng loại ảnh, thì không thể lệch. Ảnh 480×~270 chỉ khoảng 130 nghìn điểm, tính bằng Python thuần mất khoảng 0,1 s mỗi khung, 200 khung hết khoảng 20 s.

**Đã cân nhắc**: numpy ở cả hai phía bị loại, vì `tools/filmcheck` chỉ được dùng thư viện chuẩn (máy và container của worker không có numpy). JS trong trang bị loại, vì style-learn không mở trang nào.

## R2. Tách cảnh của video tham chiếu (giả định của spec, SC-001)

**Quyết định**: thêm bước `learn shots <set>` dò lại cắt cảnh bằng ffmpeg `scdet` với ngưỡng 15 (thang 0–100), hợp với điểm cắt sẵn có của `measure`. Hai điểm cắt cách nhau dưới 0,3 s thì gộp, và chớp sáng mà `measure` đã đánh dấu thì bỏ. Sau đó số cắt mỗi phút được kiểm với khoảng đã sửa trong nhật ký của `dusk-hypothetical` (16–26 lần mỗi phút): ngoài khoảng thì in cảnh báo cho người học xem lại.

**Lý do**: nhật ký sửa #1 của `dusk-hypothetical` ghi rằng phép dò hiện có chỉ ra 7,7 cắt mỗi phút, còn ngưỡng cảnh 0,15 ra 53 cắt trên 2 phút (khoảng 26 mỗi phút), khớp với lượt soát bằng mắt. Nhãn cảnh chỉ đúng khi tách cảnh đúng.

**Đã cân nhắc**: sửa luôn `motion.events` của `measure`. Bị loại, vì như vậy đổi số đo nhịp cắt của mọi phong cách đã học. Bước mới chỉ thêm dữ liệu.

## R3. Gán nhãn cỡ cảnh và góc máy (FR-002, FR-010; Clarifications)

**Quyết định**: viết module mới `tools/filmcheck/labeler.py`, theo mẫu của `editor.py` (specs/010): một lượt `claude -p` riêng, model Opus (`editor.model_args()`), chỉ có công cụ `Read`, với prompt hệ thống và JSON schema của xưởng.
- Đầu vào: các bảng ảnh cảnh (6 cột, tối đa 48 ô, mỗi ô ghi mã cảnh), cùng một danh sách mã cảnh kèm `focused_share` và vị trí ô nét nhất, để kiểm chéo.
- Đầu ra: `{shots: [{id, scale, angle, foreground_blur, confidence}]}` với:
  - `scale` ∈ {ecu, cu, med, wide, huge, insert, unknown};
  - `angle` ∈ {eye, low, high, top, ots, unknown}.
- Câu trả lời sai schema thì hỏi lại một lần. Sai nữa thì báo "chưa gán nhãn".
- Nhãn mâu thuẫn với số đo (ví dụ `ecu` mà vùng nét nằm ở góc khung và nhỏ hơn 1/12) được đánh dấu `check` để in ra cho người xem lại (FR-002).

Phim và video tham chiếu dùng **cùng** prompt và schema. Lượt gán nhãn không thấy kịch bản, phong cách hay tên phim.

**Định nghĩa cỡ cảnh** (ghi vào prompt, theo chiều cao khung so với người đứng):
- `ecu`: một phần mặt hoặc một vật nhỏ lấp khung;
- `cu`: đầu và vai;
- `med`: từ thắt lưng hoặc đầu gối lên;
- `wide`: cả người và một phần bối cảnh;
- `huge`: người nhỏ hơn 1/4 chiều cao khung, hoặc nhìn toàn cảnh;
- `insert`: thẻ chữ, đồ hoạ phẳng, không gian trống chỉ có chữ.

Góc máy:
- `eye`: ngang tầm mắt;
- `low`: máy thấp nhìn lên;
- `high`: máy cao nhìn xuống chéo;
- `top`: nhìn thẳng từ trên xuống;
- `ots`: qua vai, có đầu hoặc vai mờ ở tiền cảnh.

**Lý do**: người dùng chọn B. Một lượt Claude riêng thì độc lập với người làm phim (Clarifications), và dùng chung được cho cả hai phía (FR-010). `claude -p` đã chạy được trên máy, trong app và trong worker online, qua proxy như người biên tập.

**Đã cân nhắc**: để Claude của phiên học tự gán nhãn trong skill. Bị loại, vì khi kiểm phim phải dùng lượt độc lập, nên dùng cùng một lượt cho cả hai phía là đơn giản nhất và giữ được FR-010.

## R4. Bối cảnh (FR-004)

**Quyết định**:
- **Video tham chiếu**: mỗi khung giữa cảnh có một chữ ký màu (biểu đồ màu 4×4×4 trên ảnh 64 px, cộng độ sáng trung bình của 3×3 vùng). Gom bằng cách liên kết đơn: hai cảnh cùng bối cảnh khi khoảng cách chữ ký nhỏ hơn `SET_D`. Từ đó có số bối cảnh, tỉ lệ cảnh của bối cảnh nhiều nhất, và thời gian trung vị giữa hai lần đổi bối cảnh.
- **Phim**: dùng trường `set` của `window.SHOTS` (đã có trong hợp đồng trang của specs/020), không cần đoán.
- `SET_D` được chốt khi học lại, bằng cách xem bảng ảnh: các nhóm trông phải là cùng một nơi. Con số ghi vào research này.

**Đã cân nhắc**: để lượt gán nhãn của R3 gán cả bối cảnh. Bị loại, vì gán mã bối cảnh xuyên qua 14 bảng ảnh thì không nhất quán được.

## R5. Lưu số đo vào phong cách (FR-005, FR-007)

**Quyết định**:
- `summary.json` của bộ tham chiếu có thêm mục `shot_grammar` theo định dạng (xem data-model). Mỗi số có trung vị và khoảng giữa các video, như các số đo hiện có.
- Phong cách có thêm file máy đọc được `my-styles/<slug>/shots.json` chứa các khoảng (data-model "ShotGrammarRefs"); `stylerefs.load` đọc file này.
- Bảng "Key numbers" của `EVIDENCE.md` có thêm các hàng cách quay. Mục 6 và mục 2 (chiều sâu) của `STYLE.md` ghi con số kèm bằng chứng `sheet#ô`.

**Bằng chứng nằm ở đâu**: khung của video tham chiếu **không** được chép vào phong cách. Phong cách nằm trong git, mà hiến pháp cấm commit video tham chiếu, và `save.py` hiện chặn mọi ảnh raster lấy từ video gốc. Bằng chứng là tên bảng ảnh và ô (`v03_S014`), như các luật hiện có ("v04_0077.jpg#38–41"). Bảng ảnh và nhãn ở lại trong `references/<set>/` (ngoài git) khi `clean` chỉ xoá video và âm thanh. Đây là cách hiểu giả định cuối của spec ("khung bằng chứng được giữ lại cùng phong cách"): giữ cùng **bộ** tham chiếu, không chép vào thư mục phong cách. Người dùng đã xác nhận (2026-11-13).

## R6. Học lại một phong cách đã có (FR-008)

**Quyết định**: `learn save` có thêm cờ `--update`. Cờ này cho ghi đè một phong cách riêng đã có cùng slug, với các điều kiện:
- giữ nguyên `created`;
- thêm `updated`;
- từ chối nếu `EVIDENCE.md` mới làm mất bất kỳ dòng nào của bảng "Corrections log" cũ. So từng dòng: mọi dòng cũ phải còn; dòng mới chỉ được thêm.

Lượt học lại dùng bộ tham chiếu mới `dusk-hypothetical-2` (cùng kênh, cùng `--count 10`, cùng cách lấy mẫu).

**Lý do**: `save` hiện từ chối slug đã có. Còn kênh và các phim đều trỏ tới slug `dusk-hypothetical`, nên phải học lại vào đúng slug đó.

## R7. Phim mẫu cho phong cách học được (US4, FR-015 – FR-018)

**Quyết định**:
- Làm theo bước 5 của `MY-STYLES.md` trong thư viện (phim 15–30 s, `demo/` có `build.sh` với `LIB=…` ở đầu, `CREDITS`, `DEMO.md` theo mẫu của thư viện).
- Phim đi đủ luồng làm phim của xưởng: kịch bản được chấm, giọng của kênh, các tầng 0–4 của specs/020.
- Lưu vào `my-styles/<slug>/` gồm `DEMO.md`, `demo/`, `test.jpg` (ảnh đại diện vẽ bằng code, nhỏ) và `test.mp4`.
- **`test.mp4` không vào git**: thêm `my-styles/*/test.mp4` vào `.gitignore`. Phim dựng lại được bằng `sh demo/build.sh` (hiến pháp: không commit file media nặng; thư viện cũng không để phim trong thư mục phong cách).
- Mục 10 (Engine) của `STYLE.md` chỉ tới `demo/` trước, rồi mới tới phong cách gốc.
- Skill style-learn có thêm bước "Phim mẫu" sau bước lưu.
- `CLAUDE.md` (luồng làm phim) ghi: với phong cách riêng, đọc `DEMO.md` và `demo/` của nó trước phong cách gốc.

**Đã cân nhắc**: để phim mẫu ngoài thư mục phong cách. Bị loại, vì `MY-STYLES.md` và danh mục `my-styles/README.md` đều đặt nó ở đó.

## R8. Tầng 2 so cách quay (FR-010 – FR-014)

**Quyết định**: thêm vào `shotcheck.run`:
1. **Độ nét**: `focus.py` trên mỗi `.check/shots/<id>.jpg`. Không ô nào nét thì ra lỗi `blurred` (mức `block`, có thể ngoại lệ), với số đo là `focused_share` và độ nét của ô nét nhất.
2. **Nhãn**: lượt gán nhãn của R3 trên một bộ bảng ảnh riêng không có viền đỏ (để lượt gán nhãn không thấy kết quả kiểm). Lưu ở `.check/labels.json` cùng dấu vân tay; dấu vân tay không đổi thì dùng lại.
3. **So với `shots.json` của phong cách** (mức `warn`):
   - tỉ lệ từng cỡ cảnh và từng góc máy;
   - tỉ lệ đổi cỡ giữa hai cảnh liền nhau;
   - chuỗi cùng cỡ dài nhất;
   - trung vị `focused_share`;
   - tỉ lệ cảnh của bối cảnh nhiều nhất.

   Mỗi cảnh báo kèm mã các cảnh liên quan (ví dụ chuỗi cùng cỡ: mã từng cảnh trong chuỗi; thiếu toàn rất rộng: 5 cảnh cận dài nhất làm gợi ý).
4. Lượt gán nhãn không chạy được thì có cảnh báo `shot_grammar_unchecked`. Vì là cảnh báo nên cổng render đòi lý do (`accept-style`), không lặng lẽ cho qua.
5. Bảng ảnh có viền đỏ ghi thêm nhãn ngắn trên mỗi ô (ví dụ `P27.2 · CU · eye`).

## R9. Chi phí của lượt gán nhãn

Học lại: khoảng 1800 s video × khoảng 22 cắt mỗi phút ≈ 660 cảnh, tức 14 bảng ảnh. Hai lượt gán nhãn (lượt thứ hai chỉ cho 40 cảnh của SC-001) tốn khoảng 15 lượt xem ảnh. Phim 10 phút khoảng 200 cảnh, tức 5 bảng mỗi lần nguồn đổi. Ước tính token được ghi lại khi chạy thật.
