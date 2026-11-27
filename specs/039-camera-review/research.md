# Research: 039 Học máy quay và điểm duyệt Camera

## R1. Đo đường đi máy (camtrack)

- **Decision**: Bắt đầu từ `craft.pairs()`, tức mô hình (dx, dy, z) của mỗi cặp khung ở 12 khung/giây, ảnh xám 320×180.
  1. Cộng dồn thành đường đi: thang đo S(t) = ∏(1+zᵢ), vị trí cộng dồn theo thang đo.
  2. Tinh chỉnh tổng bằng một lần so trực tiếp khung đầu với khung cuối (bỏ 0,15 s ở hai đầu như craft) ở 640×360. Lấy đường đi cộng dồn làm phép biến đổi ban đầu, rồi dùng `block_shifts(search=2)` và `fit_camera`, lặp tối đa 3 lần.
  3. Kết quả:
     - `zoom_pct` = (S_cuối − 1)·100.
     - `drift_px` = dịch cuối quy ra 1080p.
     - `ease` = tiến độ của log S (hoặc của độ dời khi |zoom| < 0,5 %) ở ¼, ½, ¾ thời lượng.
     - `rate_pct_s` = zoom_pct / thời lượng đo.
- **Thị sai**: sau lần so trực tiếp, lấy p75 sai số còn lại của các khối nằm trong mô hình và không thuộc vùng cử động trong shot (`craft.inner`), quy ra px ở 1080p.
  - `parallax = p75 > PARALLAX_PX`. Giá trị khởi đầu là 2,0 px, hiệu chỉnh trong task bằng hai nhóm mẫu:
    - nhóm 0: 15 shot charisma-ref, số đo tay có sai số 0,2–0,4 px ở 960;
    - nhóm 1: các shot Blender orbit/dolly của bài thử 2026-11-26 (`/mnt/e/claude-utube-ae/blendertest`), nếu còn, nếu không thì video tổng hợp hai mặt phẳng.
  - Ngưỡng được đặt ở giữa hai nhóm và ghi vào `camtrack.py` kèm số đo.
- **Rationale**: craft.py đã có khớp khối và khử ngoại lai, nhưng chỉ ra trung vị tốc độ. Cộng dồn các cặp ở 320 px trôi khoảng 0,1 %/s, nên cần lần so trực tiếp để tổng zoom lệch ≤ 1 điểm phần trăm (SC-001). Cách đo của `deep.py` (LK + RANSAC ở 960) cần OpenCV, không có trong venv học.
- **Alternatives**: thêm OpenCV (nặng thêm, trái nguyên tắc V); chỉ dùng tốc độ trung vị × thời lượng (sai khi có ease, đúng là lỗi của charisma-30).
- **Kiểm chứng**: video tổng hợp có zoom 3/6/9 %, ease 0,13/0,48/0,85 và trôi 0/8/12 px phải đo lệch ≤ 0,3 điểm phần trăm và ≤ 2 px. Video hai lớp có thị sai phải ra `parallax: true`. Trên 15 shot charisma-ref, so với `deep_ref.json` (pan_px của deep.py đo ở 960 → ×2).

## R2. Bố cục

- **Decision**: craft-label bản 2 thêm `subject: [x0, y0, x1, y1]`, là phần trăm khung của người chính (null khi không có người hoặc là thẻ). Từ đó suy ra `subject_x`, `subject_y` (tâm), `subject_h` (chiều cao so với khung) và `headroom` (y0). Phiên bản prompt đổi nên cache nhãn cũ được bỏ đúng cách (craftlabel.version()).
- **Rationale**: không có bộ dò người trong venv; craft-label đã xem từng shot qua một lượt Claude độc lập. Thêm một ô vào schema rẻ hơn thêm một lượt mới.
- **Alternatives**: dùng tâm vùng cử động của craft.inner (không phải người chính); dùng bộ dò người như YOLO (thêm mô hình và trọng số).

## R3. Lưu thư viện và khung bằng chứng

- **Decision**:
  - `learn camera SET [--videos v01,…]` ghi `references/<set>/profile/<vid>/camera.json`, mỗi shot một mục và mã `vid:Sxxx` lấy từ `shots.json`.
  - `learn save` ghi `my-styles/<style>/camera.json`, gồm `version`, `shots[]` (số, không ảnh), `by_size{}` và `transition_main`.
  - Khung bằng chứng ở `my-styles/<style>/camera/<vid>-<id>-{a,b}.jpg`, rộng 360 px, chỉ cho tối đa 150 shot. Các shot có ảnh được chọn phân tầng theo (cỡ cảnh × loại chuyển động) và theo độ tin cậy.
  - Lệnh gợi ý ưu tiên shot có ảnh khi điểm giống chênh dưới 0,1.
  - `camera suggest --set SET` đọc thẳng `references/<set>/profile` (cho bộ thử charisma-ref chưa thành phong cách).
- **Rationale**: dusk-hypothetical-3 có 2192 shot, mà 2 ảnh 640 px mỗi shot thì quá nặng cho git. Hiến pháp chỉ cho giữ "vài khung làm bằng chứng". Tệp riêng `camera.json` cạnh `shots.json` (nơi có khối depth) để không làm phình tệp mà depthcheck đang đọc.
- **Alternatives**: nhét vào `shots.json` (to, đụng 038); giữ ảnh mọi shot (nặng).

## R4. Độ giống giữa shot phim và shot mẫu

- **Decision**: điểm = Σ trọng số × khớp, chia cho tổng trọng số của các trường mà phim có.
  - card 3 (khác nhau thì loại)
  - cỡ cảnh 3 (khớp 1, kề nhau 0,5)
  - số người theo nhóm 0/1/2/3+ là 2
  - action 2, outdoor 1, prop 1
  - thời lượng 1: max(0, 1 − |ln(d_phim/d_mẫu)|/ln 3)
  Mỗi phương án ghi lại các khớp (`why: {size:1, people:1, action:0, …}`). Trọng số nằm trong một bảng của `camsuggest.py`. Bài test cố định thứ tự trên tập nhỏ.
- **Trường bên phim**: `shot_plan` thêm `card`, `action`, `outdoor`, `prop` (bool, tuỳ chọn), cùng định nghĩa với craft-label để hai bên nói cùng một ngôn ngữ. `people` và `size` đã có.
- **Rationale**: giải thích được trong một dòng (FR-007), chạy định sẵn, không tốn lượt Claude.
- **Alternatives**: hỏi Claude chọn shot mẫu (không ổn định, khó kiểm); embedding ảnh (chưa có ảnh của shot phim trước khi dựng).

## R5. Sinh phương án

- **Decision**:
  - **Phương án 1 (khuyên dùng)**: máy của shot mẫu giống nhất.
    - Giữ tốc độ zoom và trôi mỗi giây, nhân với thời lượng của shot phim, rồi kẹp vào p25–p75 của `by_size[size]`.
    - Ease lấy theo shot mẫu; shot mẫu kém tin cậy thì lấy trung vị của cỡ cảnh.
    - Chuyển cảnh = `transition_main`.
  - **Phương án 2**: shot mẫu tốt nhất khác phương án 1 ở cỡ cảnh hoặc chiều zoom.
  - **Phương án 3**: từ bảng tổng của cỡ cảnh kề (rộng hơn một bậc), hoặc "đứng" nếu video mẫu có ≥ 15 % shot đứng ở cỡ cảnh đó.
  - Bỏ phương án trùng (cùng cỡ cảnh, cùng chiều, zoom lệch < 1 điểm phần trăm).
  - Phương án ngoài p25–p75 phải có `note`.
  - Khi `parallax_share < 0.05`, mọi phương án có `move ∈ {static, push, pull, pan}` và shot nền Blender có máy đứng yên (FR-009).
  - Bộ máy nền: giữ `shot_plan.engine`; phim chưa ghi thì wide/huge → blender, còn lại → ae (luật R11 của 038).
- **Start framing**: `start.scale` = tỉ lệ để người chính có chiều cao `subject_h` của shot mẫu, so với chiều cao người trong bản dựng ở thang đo 1. Chiều cao đó lấy từ marks của bản dựng; chưa có thì dùng chiều cao mặc định của rig ở cỡ cảnh đó. `start.cx/cy` theo `subject_x/y`. Kẹp sao cho khung không lộ mép (giống `camInside`).

## R6. Thời lượng trước và sau Voice

- **Decision**: trước Voice, thời lượng shot lấy từ `timing.json` nếu có, nếu không thì từ danh sách shot của phim (`shots.json` [t0, t1, set, id]). Sau khi `timing.json` đổi (voice, `animatic fit|accept`), `camera retime` tính lại zoom và trôi theo `rate_pct_s` đã chọn, in các shot có số mới, và không đổi dấu vân tay của điểm Camera.
  - Lệnh `animatic accept` và `voice make` gọi retime khi có `camera/options.json`.
- **Rationale**: người dùng chọn Camera trước Voice (Clarifications); FR-011.

## R7. Chuyển động máy trong bộ dựng

- **AE**: `bundle.py` ghi `data/camera.json` = {shot: camera} từ `shot_plan`. `CU.planCam(comp, shot, dur)` trong `lib.jsx` là bản chung của `CU.CAMFIT`/`fitCam`/`easeEnds` của charisma-30:
  - đặt khoá đầu và cuối cho null CAM (scale, position);
  - dùng ease tốc độ 0 với ảnh hưởng (influence) vào/ra. Python chọn hai số này từ bảng tra (influence → tiến độ ở ¼½¾ của đường Bézier AE, tính sẵn trong `camsuggest.py`) sao cho gần ease đã chọn nhất.
  - `camFromMotion` (motion/S#.json) vẫn được ưu tiên nếu có, để phim cũ không đổi.
- **Blender**: `camera.py` đã có `move == "zoom"` (máy đứng, tăng tiêu cự, `shift`, `ease=(in,out)`). Khối camera được đổi thành các tham số đó; máy không đi, không vòng. Zoom bằng tiêu cự quanh tâm ảnh tương đương zoom 2D, nên không có thị sai.
- **Phim cũ**: không có `shot_plan.camera` thì không có gì đổi (FR-020).

## R8. Ảnh thử ¼

- **Decision**: `camera stills <film> [--shots …]`:
  - **Shot AE**: dùng lại `ae draft` ở chế độ `--still`. Bản dựng ¼ (resolutionFactor 4) chỉ khung 1 của mỗi phương án; mỗi phương án là một bản sao comp của shot với `planCam` riêng; cả lượt đi một hàng đợi AE. Không cần giọng: bỏ kiểm `voice_ready` khi `--still`, chỉ dùng thời lượng của R6.
  - **Shot Blender**: một `blender build <film> S# --still 1 --quarter` cho mỗi shot (máy đứng yên, nhân vật là lớp do rig AE xuất như 038). Phương án là khung bắt đầu cắt từ ảnh đó, phóng lên 480×270.
  - Vẽ khung chữ nhật của khung cuối (màu vàng, 2 px) bằng Pillow → `films/<f>/camera/stills/S#-o<n>.jpg`.
  - Thiếu AE hoặc Blender thì dừng và báo (hiến pháp VII).
- **Rationale**: người dùng chọn "ảnh ¼ cỡ thật + khung zoom".
- **Alternatives**: phác thảo khối hình (người dùng không chọn).

## R9. Điểm duyệt Camera

- **Decision**: `points.POINTS` thêm `"camera"` sau `"cast"`; `AE_ON` và `AE_ONLY` thêm `"camera"`; `steps.py` thêm bước Camera giữa Cast và Voice.
  - **fingerprint**: băm danh sách shot, các trường plan dùng cho độ giống, mã phương án đã chọn và các thông số không phụ thuộc thời lượng (`rate_pct_s`, ease, size, start). Retime không làm "Must run again".
  - **reached**: có `options.json` phủ mọi shot và có ảnh thử.
  - **checks_pass**: mọi shot đã chọn và không có ghi chú mở (giống nhánh cast).
  - `voice make` gọi `gate(camera)` sau `gate(cast)`.
  - Phim không có thư viện máy quay thì điểm bị bỏ qua, ghi lý do (FR-020).

## R10. Ghi chú và việc sửa

- **Decision**: `camnotes.py` dùng sổ `pins.py`: `films/<f>/camera/notes.json`, nhóm `shots`, ghim theo (shot, phương án, x %, y %).
  - `reviews.decide` của điểm camera lấy note từ `camnotes.summary`, giống animatic/sound.
  - Việc sửa chạy `camera suggest --shots <ghi chú> --keep-others` rồi `camera stills --shots …`, nên các shot khác giữ nguyên từng byte.

## R11. Trang Camera

- **Decision**: thêm `cameraPanel` trong `app.js`, theo mẫu `doneAnimatic`/`animNoteBox`/`castPins`.
  - Lưới shot; bấm một shot thì các phương án hiện cạnh nhau, gồm ảnh thử, khung shot mẫu, số đo và lý do.
  - Xem trước zoom bằng CSS `transform` trên ảnh thử, `cubic-bezier` khớp ease.
  - Chọn qua `sendEdit` → `camera_choose`; ghim qua `camera_note_add`/`camera_note_remove`, đều là op trong `edit.py` và nằm trong danh sách cho phép `actions.OPS["camera"]`.
  - Ảnh phục vụ qua route ảnh của phim đã có (như animatic frames). `filmsteps.camera_block()` trả dữ liệu cho panel.

## R12. Kiểm máy quay

- **Decision**: `qc camera <film>` đo `animatic/shots/S#.mp4` (480×270, nên đo ở cỡ gốc) hoặc clip shot của bản đẹp bằng `camtrack.measure`, rồi so với `shot_plan.camera`. Các luật:
  - `cam_zoom`: lệch > 1 điểm phần trăm
  - `cam_dir`: sai chiều
  - `cam_ease`: tiến độ ½ lệch > 0,10
  - `cam_parallax`: có thị sai khi phương án không có
  - `cam_transition`: chuyển cảnh khác phương án
  Kết quả là tier `camera` trong `tiers.py`. Miễn theo shot qua `tiers.add_exception`, cái này từ chối khi chạy trong việc của app. Không chặn `ae render`: spec chỉ yêu cầu báo.
- **Rationale**: dùng đúng cách đo của US1 (FR-005); khung tier và miễn đã có ở depthcheck.

## R13. Ngoài phạm vi

- `ae plan --suggest` của 038 (T050/T051) không làm ở đây. Phương án chỉ ghi bộ máy nền theo R5.
- Không học hay đề xuất máy đi thật khi video mẫu không có (FR-009).
