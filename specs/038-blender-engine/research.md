# Research: 038 Blender là bộ máy thứ ba, bộ máy theo shot, chiều sâu

Mỗi mục: Quyết định · Lý do · Phương án đã cân nhắc.

## R1. Hiến pháp 4.0.0, nguyên tắc VII

- **Quyết định**: Viết lại VII thành "Ba bộ máy dựng hình":
  - trang web: giữ nguyên
  - After Effects: render trong hàng đợi render của chính AE, AE để mở. Sửa luôn chữ "dựng bằng aerender" cho đúng với code của specs/032.
  - Blender: phần mềm miễn phí do người dùng tự cài, xưởng không tải, cài hay đóng gói.
  - Phim hoạt hình nhân vật (`engine: "ae"`) được có shot Blender. Phim trang web chỉ dùng một bộ máy.
  - Mọi hình do code của xưởng hoặc do Claude Code viết sinh ra; không dùng mô hình AI tạo ảnh hay video.

  Tăng lên 4.0.0 (MAJOR) vì bỏ luật "mỗi phim đúng một bộ máy".
- **Lý do**: Người dùng chọn "Trộn theo cảnh" (2026-11-26). Luật cũ cấm trộn.
- **Phương án đã cân nhắc**: Bản 3.1.0 chỉ thêm Blender làm bộ máy cho cả phim. Bị loại vì người dùng đã chọn trộn theo shot.

## R2. Khai báo bộ máy theo shot mà không phá phim AE cũ

- **Quyết định**: `film.json` giữ nguyên `engine: "ae"` và danh sách `shots`, thêm khối tuỳ chọn `shot_plan` (theo mã shot):
  - `engine`, `suggested`, `reason`
  - các trường chiều sâu: `size`, `cam_height`, `lens`, `depth`, `layers`, `occluder`
  - `set`

  Thêm `default_engine` (mặc định `"ae"`). Shot không có trong `shot_plan` thì là shot AE. Phim cũ không có khối này nên dựng y như trước (SC-009).
- **Lý do**: `film.py` đang kiểm `shots` bằng regex và mọi lệnh đều đọc nó. Thêm một khối riêng thì không đụng tới các lệnh hiện có.
- **Phương án đã cân nhắc**: Đổi `shots` thành danh sách object. Bị loại vì phá `pick_shots`, `bundle`, `draft`, `sheet` và test.

## R3. Ghép bản tổng của phim trộn

- **Quyết định**: `ae build` tách shot theo bộ máy:
  - **Shot AE**: dựng như hiện nay thành một `master.mp4` riêng của nhóm AE, kèm mốc.
  - **Shot Blender**: mỗi shot ra một `S<n>.mp4`.
  - **Ghép**: hàm `assemble()` mới trong `tools/ae/splice.py` ghép theo thứ tự của phim. Đoạn AE lấy bằng `pieces_from_master`, đoạn Blender lấy nguyên tệp. Dùng một filter ffmpeg trim/concat như `splice()`, libx264, đúng số khung từng shot theo `timing.json`.

  `shots.json` giữ mảng `[[t0,t1,set,id]]` (định dạng của specs/029), thêm `"source": "mixed"` và `"engines": {id: {engine, version}}`.

  `ae fix` dùng lại `plan()` và `splice()`: shot Blender bị sửa thì dựng lại `S<n>.mp4` rồi ghép theo khung vào video hiện có.
- **Lý do**: `splice.plan/splice` đã đúng khung và có test. Thêm nguồn "tệp shot" là cách nhỏ nhất.
- **Phương án đã cân nhắc**:
  - Đưa clip Blender vào AE làm footage để AE ghép: bắt mọi lượt dựng Blender đi qua AE, chậm và nặng.
  - Chuyển cảnh trong từng bộ máy: không làm được giữa hai bộ máy, nên chuyển cảnh mờ dần hoặc đen để cho ffmpeg làm lúc ghép (FR-010).

## R4. Chạy Blender: trên máy (WSL) và trong app

- **Quyết định**:
  - **Cấu hình máy**: `~/.config/claude-utube/blender.json` (hoặc `$STUDIO_BLENDER_CONFIG`), các khoá:
    - `blender`: đường dẫn Windows hoặc macOS
    - `work`: thư mục Windows nhìn thấy được, ví dụ `/mnt/e/claude-utube-ae/blender`
    - `shotTimeoutSec` (mặc định 3600)
    - `secPerFrame`: đo sau mỗi lượt, dùng để in ước tính
  - **Lệnh**: `blender.exe -b --factory-startup -P <work>/<run>/kit/entry.py -- <work>/<run>/request.json`. Trên WSL, đường dẫn đổi bằng `wslpath -w`.
  - **Nhật ký** `log.txt` ghi các dòng giống AE: `START`, `GPU <renderer>`, `frame S<n> <i>/<N>`, `shot S<n> ok`, `ERR <code> <msg>`, `DONE`.
  - **Khung hình**: PNG ghi với `use_overwrite=False` và `use_placeholder=True`, nên lượt sau dựng tiếp từ khung đã có (FR-008). Sau khi dựng, ffmpeg phía xưởng đóng thành `S<n>.mp4`.
  - **Trong app**: qua cầu nối Blender (R8).
- **Lý do**: Bản thử đã chạy đúng cách này: Blender 5.2.5 portable, EEVEE trên Intel UHD 730, khoảng 5,5 s mỗi khung 1080p. Dùng cùng định dạng nhật ký với AE thì `wait_log` và tiến độ dùng chung được.
- **Phương án đã cân nhắc**:
  - Blender bản Linux trong WSL: chỉ dựng bằng phần mềm (llvmpipe), vi phạm luật GPU.
  - Blender đóng gói như module Python (`bpy` từ pip): không có GPU của Windows, và gói nặng.

## R5. Bắt buộc GPU

- **Quyết định**: `kit/core.py` gọi `gpu.platform.renderer_get()` và `gpu.platform.backend_type_get()` trước khung đầu. Tên khớp `llvmpipe|softpipe|swrast|SwiftShader|Microsoft Basic Render|Software` thì ghi `ERR gpu_software <tên>` và thoát mã 3, không ra khung nào (FR-025, SC-008). Dòng `GPU <tên>` được ghi vào mốc shot. `sh bin/studio status` thêm dòng Blender: chạy một script dò khoảng 3 s, kết quả lưu 10 phút trong `~/.cache/claude-utube/blender-probe.json`.
- **Lý do**: Bản thử đã ghi `GPU Intel(R) UHD Graphics 730 OPENGL` bằng chính cách này. Memory của người dùng yêu cầu GPU bắt buộc, phần mềm thì dừng và hỏi.
- **Phương án đã cân nhắc**: Kiểm thời gian mỗi khung (chậm thì cho là phần mềm). Bị loại vì không chắc chắn.

## R6. Nhân vật trong shot Blender: lớp do AE xuất (câu 3 của clarify)

- **Quyết định**: Mỗi shot Blender có nhân vật chạy ba lượt:
  1. **Lượt tính** (Blender, không render, vài giây): chạy script shot, rồi với mỗi nhân vật và mỗi khung tính:
     - hướng nhìn của máy so với hướng nhân vật, đổi ra góc của rig: `front`, `34` với `dir` ±1, `back`. Đổi góc chỉ khi lệch quá 15° so với ranh giới, để không nhấp nháy.
     - chiều cao nhân vật trên màn hình (px)

     Kết quả ghi vào `layers.json`: mỗi nhân vật có danh sách góc cần dùng, động tác theo khung (tên trong `catalog.json` của rig: `walk`, `poses`, `expressions`) và cỡ cần dựng (chiều cao lớn nhất × 1,2, tối đa 1080 px).
  2. **Lượt lớp** (AE): bundle mới loại `layers`, file `kit/castlayer.jsx`. Với mỗi (nhân vật, góc) dựng một comp chỉ có rig, nền trong suốt, đủ thời lượng shot, động tác như trong `layers.json`. Render ra **chuỗi PNG có kênh alpha**: cài output module bằng `setSettings` ("PNG Sequence", "RGB + Alpha"). Nếu không cài được thì dùng template "Lossless with Alpha" đã kiểm ở task thử. Tên tệp: `L<shot>-<char>-<view>/f####.png`. Cầu nối gói thư mục thành `.tar` khi gửi (tên kết quả mới `L…`).
  3. **Lượt dựng** (Blender): mỗi nhân vật là một nhóm mặt phẳng, mỗi góc một mặt phẳng, gắn chuỗi PNG làm texture (Image Sequence, `alpha blend`, bóng `alpha clip`). Chỉ hiện mặt phẳng của góc đang dùng ở mỗi khung. Mặt phẳng quay quanh trục đứng về phía máy (ràng buộc Locked Track Z), gốc ở chân, nên có bóng đổ xuống sàn và được che theo chiều sâu thật.

  Đám đông (hơn 8 người) dùng một bộ nhỏ lớp đã dựng (4 nhân vật × động tác ngồi, vỗ tay), lệch thời gian và lật trái/phải, để AE không phải dựng hàng chục lớp.
- **Lý do**:
  - Một bản code nhân vật duy nhất, nên hình ở hai bộ máy là một (SC-006).
  - Rig chỉ chọn góc lúc dựng comp, nên phải dựng mỗi góc thành một lớp riêng.
  - Đường dẫn làm việc của AE và Blender cùng nằm trên ổ Windows, nên lượt lớp không phải chép.
- **Kết quả thử thật (T040, 2026-11-27, AE 2027)**:
  - `om.setSettings({"Format": "PNG Sequence", ...})`, cả dạng phẳng lẫn dạng lồng `"Video Output"`, đều bị AE từ chối: "Invalid Value for key: <Format>. Property is read-only".
  - Template `"Lossless with Alpha"` chạy được, ra AVI `rawvideo` `bgra`. Kiểm khung 1: góc (0,0,0,0) trong suốt, giữa (230,77,51,255) đặc.
  - **Chốt cách làm**:
    - AE render mỗi lớp thành `L<shot>-<char>-<view>.avi` bằng template này.
    - Máy chủ tách AVI thành `f####.png` RGBA bằng `ffmpeg -i x.avi -pix_fmt rgba f%04d.png`, rồi xoá AVI (≈ 4,7 MB mỗi khung 1080²).
    - Tên thư mục và cách Blender đọc giữ nguyên.
  - **Bẫy**: lỗi trong khối `catch` của script `-r` làm AE bật hộp thoại lỗi và đứng chờ. Mọi lệnh `-r` sau đó bị giữ lại cho đến khi bấm OK. Script lớp phải ghi log từng dòng (mở, ghi, đóng ngay), và không đặt tên biến trùng với tên biến của catch.
- **Phương án đã cân nhắc**:
  - ProRes 4444 `.mov`: một tệp mỗi lớp, nhưng không chắc Blender đọc được alpha của ProRes. PNG chắc chắn đọc được.
  - Dựng sẵn thư viện động tác: bị loại theo câu 3 của clarify.
  - Viết lại rig bằng Python cho Blender: bị loại theo câu 3 của clarify.

## R7. Bộ dựng Blender dùng chung

- **Quyết định**: `tools/blender/kit/` (Python chạy bên trong Blender, chỉ dùng `bpy`, `bmesh`, `mathutils`, `gpu`), viết lại từ `bl.py` của bản thử:

  | Tệp | Nội dung |
  |---|---|
  | `core.py` | cài cảnh, render, GPU, nhật ký, khung dựng tiếp |
  | `toon.py` | vật liệu hai tông và vệt nắng ấm, `head_mat` không dùng; viền inverted hull |
  | `mesh.py` | khối cơ bản |
  | `camera.py` | khoá máy, ống kính theo lớp `lens`, DOF, `look_at` |
  | `cards.py` | mặt phẳng nhân vật, đám đông, bóng |
  | `fx.py` | hoa giấy |
  | `plate.py` | ảnh nền cho shot AE |
  | `sets/` | `classroom.py`, `hallway.py`, `auditorium.py` |
  | `entry.py` | đọc `request.json`, chạy từng shot |

  Shot của phim nằm ở `films/<tên>/blender/S<n>.py`, định nghĩa `def shot(k):` gọi bộ dựng qua đối tượng `k`. `tools/blender/uses.py` tìm các hàm và bối cảnh mà mỗi shot dùng (`k.<tên>(`, `k.set("<tên>")`).

  Phần thuần Python (kế hoạch, đọc `film.json`, ước tính, nhật ký) nằm ở `tools/blender/*.py` ngoài Blender, có test bằng unittest.
- **Lý do**: Giống cách chia giữa `tools/ae/kit` và `tools/ae/*.py`. Phim không chép bộ dựng (FR-007).
- **Phương án đã cân nhắc**: Một tệp `bl.py` lớn. Bị loại vì khó tìm shot nào dùng gì (FR-006).

## R8. Cầu nối Blender trong app

- **Quyết định**:
  - **Hàng đợi**: tổng quát hoá `tools/ae/aequeue.py` thành `tools/ae/enginequeue.py`, tham số `engine` ∈ {`ae`, `blender`}, thư mục `$STUDIO_DATA/<engine>/requests/`. `aequeue.py` giữ nguyên các hàm, chỉ gọi sang module chung với `engine="ae"`. Tên kết quả nhận thêm `L<shot>-<char>-<view>`.
  - **Đường gọi**: core thêm `/api/v1/blender/bridge/...` (cùng dạng `/api/v1/ae/bridge/...`), proxy thêm `/internal/blender/requests`.
  - **App**: `desktop/blenderbridge.js` theo khuôn `aebridge.js`:
    - khoá `x-cu-bridge` dùng chung với cầu nối AE
    - mỗi lúc một lượt
    - hạn mỗi shot = `shotTimeoutSec`
    - `findBlender()`: Windows `C:\Program Files\Blender Foundation\Blender */blender.exe`, macOS `/Applications/Blender.app/Contents/MacOS/Blender`
  - **Trang chọn đường dẫn**: `desktop/blender.html` (như `ae.html`).
  - **Bài thử**: `desktop/test/fake-blender.mjs` và `blenderbridge.test.js`. `desktop.yml` thêm hai dòng chờ: "blender bridge ok", "blender build ok".

  Lượt lớp của shot Blender đi qua cầu nối AE (loại bundle `layers`).
- **Lý do**: Spec FR-026, FR-028 (câu 2 của clarify). Dùng lại khuôn đã chạy thật ở specs/032.
- **Phương án đã cân nhắc**: Một cầu nối chung cho hai bộ máy, chạy song song. Bị loại vì hai bộ máy có cách khởi động, hạn giờ và kết quả khác nhau. Hai lớp mỏng dùng chung hàng đợi thì đơn giản hơn.

## R9. Đo chiều sâu trên video mẫu

- **Quyết định**: Mở rộng `tools/filmcheck/labeler.py` (một lượt Claude độc lập, luôn `models.current()` = Opus 5.5), thêm vào `SCHEMA` mỗi shot:
  - `cam_height`: low / eye / high / top
  - `lens`: wide / normal / long
  - `depth`: shallow / mid / deep
  - `layers`: các lớp cảnh có thật: fg, mid, bg, far
  - `occluder`: có vật che ở tiền cảnh hay không

  Tăng `LABELER_VERSION` để bỏ cache cũ. Vẽ lại hình hướng dẫn `labeler-guide.png` bằng `tools/style-learn/sl/guide.py`, thêm ba dải ví dụ vẽ bằng code (độ cao máy, ống kính, lớp cảnh).

  Số đo bằng công cụ, file `tools/filmcheck/vanish.py`: OpenCV (đã có trong `tools/.venv`), Canny + HoughLinesP, gom điểm tụ.
  - Có một điểm tụ: ra vị trí đường chân trời (tỉ lệ chiều cao khung).
  - Có hai điểm tụ vuông góc: ước lượng góc nhìn ngang.

  Hai số này vừa là gợi ý gửi kèm cho labeler (tham số `hints` đã có), vừa được ghi làm bằng chứng. Labeler và điểm tụ lệch nhau thì shot được đánh `check` để người dùng xem lại.

  Phong cách thêm khối `depth` trong `my-styles/<slug>/shots.json`. Với mỗi cỡ cảnh:
  - tỉ lệ từng `cam_height`, `lens`, `depth`
  - `layers_p25`, `layers_p50`
  - `occluder_share`
  - `n`
  - khung bằng chứng
- **Lý do**: Hiến pháp VIII (đo, có bằng chứng). Labeler của specs/021 đã đạt 0,80–0,97 trên cỡ cảnh và góc máy. Điểm tụ giúp hai nhãn khó (độ cao máy, ống kính) có thêm căn cứ đo được. SC-005 đòi khớp ≥ 80%.
- **Phương án đã cân nhắc**:
  - Mô hình ước lượng độ sâu (MiDaS và tương tự): thêm phụ thuộc nặng, và với hình hoạt hình phẳng thì không chắc đúng.
  - Chỉ dùng điểm tụ: nhiều shot cận không có đường thẳng để tính.

## R10. Tầng kiểm chiều sâu (chặn theo shot, câu 1 của clarify)

- **Quyết định**: Module mới `tools/filmcheck/depthcheck.py`, lệnh `sh bin/studio qc depth <phim>`.
  - **Đầu vào**:
    - `shot_plan` của phim
    - nhãn chạy trên chính phim: khung giữa của `animatic/shots/S#.mp4`, hoặc một khung dựng nhanh ở ¼ cỡ, labeler như trên
    - khối `depth` của phong cách mà kênh của phim dùng
  - **Luật theo shot** (chặn), so với video mẫu ở cùng cỡ cảnh:
    - `depth_close`: shot chặt hơn cỡ cảnh đã khai báo, hoặc dùng `lens: long` trong khi video mẫu có dưới 10% `long` ở cỡ cảnh đó
    - `depth_shallow`: số lớp ít hơn `layers_p25`, hoặc `depth` thấp hơn mức thấp nhất mà video mẫu dùng ≥ 25% ở cỡ cảnh đó
    - `card_angle`: góc giữa trục máy và mặt phẳng nhân vật vượt 75°. Số đo lấy từ lượt tính của Blender, theo FR-019.
  - **Cảnh báo cả phim**: tỉ lệ một cỡ cảnh lệch quá 10 điểm phần trăm. Cỡ cảnh có `n < 5` chỉ cảnh báo (FR-015).
  - **Lưu kết quả**: `checks.json` ở `tiers.depth`, có dấu vân tay.
  - **Chặn**: `ae render` (bản đẹp) gọi `depthcheck.gate()` cạnh `points.gate(…,"animatic")`. Còn lỗi chặn thì thoát mã 1 và liệt kê shot.
  - **Miễn**: thêm `depth_close`, `depth_shallow`, `card_angle` vào `EXCEPTABLE`. `qc except` từ chối khi biến `STUDIO_JOB` có mặt (FR-014). Hiện chưa có chặn này trong code, chỉ có lời dặn trong JOB.md.
- **Lý do**: Người dùng chọn A ở câu 1 của clarify. Dùng lại cơ chế `tiers` và `qc-exceptions.json` có sẵn.
- **Phương án đã cân nhắc**: Kiểm ngay trong `qc shots` của phim web. Bị loại vì phim AE không chạy `qc shots`. Phim AE có bản nháp Animatic, nên đó là chỗ lấy khung hợp lý.

## R11. Gợi ý bộ máy theo shot

- **Quyết định**: `tools/ae/suggest.py` theo luật cố định, không gọi AI:
  - **Blender** khi gặp một trong các điều kiện:
    - `size` ∈ {wide, huge}
    - máy có `move` ∈ {dolly, orbit, track, crane}
    - có từ 6 người trở lên
    - `set` có trong danh sách bối cảnh Blender
  - **AE** khi `size` ∈ {ecu, cu, insert} hoặc shot là thẻ chữ hay đồ hoạ.
  - Trường hợp còn lại (`med`): AE, trừ khi máy đi.

  Lý do gợi ý ghi bằng một câu tiếng Anh ngắn, ví dụ `"wide + dolly in a deep set"`. Lệnh: `sh bin/studio ae plan <phim> [--suggest] [--set S3 engine=blender …]`. Lệnh ghi `suggested`, `reason`, và `engine` nếu shot chưa có.
- **Lý do**: Luật rõ, tự kiểm được và không tốn token. SC-007 đòi trùng ≥ 80% với lựa chọn của người dùng, luật chỉnh được theo kết quả phim thử.
- **Phương án đã cân nhắc**: Hỏi Claude cho từng shot. Đắt hơn và khó kiểm, nên chỉ cân nhắc nếu luật không đạt SC-007.

## R12. Bảng mẫu Cast cho phim trộn và ảnh nền cho shot AE

- **Quyết định**:
  - **Bảng mẫu Cast**: khi phim có shot Blender, `ae sheet` dựng thêm cho mỗi nhân vật một hình trong "sân khấu Cast" Blender (sàn, nền, đèn của bộ dựng, máy ngang ¾), dùng lớp do AE xuất ở cùng tư thế với hình AE. Hai hình được đặt cạnh nhau trong `cast/sheets`.
  - **Kiểm số đo** (SC-006): đo màu áo và màu đầu bằng ΔE2000 trên vùng mặt nạ, đo độ dày viền bằng biến đổi khoảng cách, viết trong `tools/ae/sheet.py`.
  - **Ảnh nền cho shot AE** (FR-020): `sh bin/studio blender plate <phim> S5 --from S4` dựng một khung của bối cảnh shot S4 ở góc máy khai báo cho S5, không có nhân vật, ghi vào `films/<tên>/ae/data/plates/S5.png`. Shot AE dùng ảnh đó bằng `CU.plate("S5")` (hàm mới trong `kit/lib.jsx`).
- **Lý do**: FR-018, FR-020. Dùng lại đường bundle `data/**` có sẵn (≤ 50 MB).
- **Phương án đã cân nhắc**: AE vẽ lại bối cảnh 2D cho shot cận. Lệch màu và ánh sáng với cảnh toàn Blender ngay cạnh.

## R13. Test

- **Quyết định**:
  - **`tests/blender/run.sh`** (unittest), dùng Blender giả (`STUDIO_BLENDER_FAKE=1` → `node desktop/test/fake-blender.mjs`: đọc `request.json`, ghi `log.txt` và khung PNG bằng ffmpeg testsrc, có các chế độ `gpu_software`, `hang`, `err`). Kiểm:
    - `film.json`/`shot_plan`, gợi ý, `uses`
    - ghép phim trộn (khung đúng ±1)
    - `fix` chỉ dựng lại shot đổi
    - dựng tiếp sau khi ngắt, chặn GPU
    - `layers.json`, `depthcheck`, `qc except` trong việc
  - **`tests/blender/live.sh`**: chạy thật với Blender đã cài. Dựng một shot 1 s ở ¼ cỡ, kiểm dòng GPU. Không vào bộ 5 suite vì cần GPU.
  - **Mở rộng**: `tests/ae/run.sh` (bundle `layers`, `castlayer.jsx` với AE giả), `tests/filmcheck/run.sh` (labeler schema mới, `vanish.py` trên ảnh vẽ bằng code), `desktop` (`blenderbridge.test.js`).
- **Lý do**: Hiến pháp IV. Cách làm giống `tests/ae` với AE giả.

## R14. Nguồn ngoài (tìm 2026-11-26) và chỗ dùng

| Cách làm ngoài ngành | Dùng ở đâu |
|---|---|
| **Layout**: dàn cảnh từng shot bằng bối cảnh, nhân vật và máy 3D sau animatic, giữ nhịp của animatic (Disney Animation, layout notes của UW CSE458). Dựng khối 3D trước, nhân vật 2D sau (Blender Studio, "Cat Purkour"). | 038: shot Blender đặt máy trong bối cảnh liền, rồi mới có lớp nhân vật (R6). |
| **Khớp máy theo ảnh**: fSpy và Perspective Plotter dùng điểm tụ để tính tiêu cự, độ cao và góc máy. Một điểm tụ thì không xác định được tiêu cự. | 038: `vanish.py` ra chân trời và góc nhìn. Chỉ tin `hfov` khi có hai điểm tụ (R9). |
| **Máy 3D làm lộ nhân vật phẳng**: Blender Studio cảnh báo máy đi tạo thị sai làm lộ chất 3D, nên phải lên kế hoạch máy theo cách của phim 2D. | 038: luật `card_angle` (> 75°). Shot có nhân vật thẻ ưu tiên dolly và đẩy hơn là orbit. |
| **Chuyển động máy trong shot**: optical flow Farnebäck (OpenCV) phân loại static/pan/tilt/zoom. Các bộ dữ liệu MOVE-SET và HISTORIAN có sẵn nhãn. Zoom và dolly khó tách nhau. | 039: đo máy chạy trong shot của video mẫu. |
| **Nối shot mượt**: cắt khi nhân vật đang làm động tác, giữ hướng chuyển động và tốc độ qua chỗ cắt, độ sáng không nhảy, luật 180°, ít hiệu ứng chuyển cảnh. | 039: đo hướng và tốc độ chuyển động, cùng độ sáng, ở hai phía chỗ cắt của video mẫu; dùng làm luật gợi ý trên trang Camera. |
| **Sơ đồ nhìn từ trên xuống**: vẽ bối cảnh và vị trí từng máy cho cả cảnh (shot plan, coverage master/OTS/reverse). | 039: một bối cảnh liền, nhiều máy; sơ đồ để người dùng duyệt. |
| **Camera tracking của Blender** trên video thật: cần ít nhất 8 điểm bám, chịu kém với hình mờ do chuyển động. Hoạt hình phẳng ít chi tiết nên khó bám. | Không dùng. Optical flow toàn khung đủ cho 039. |

## R15. Nguồn GitHub về góc máy và chuyển cảnh (đầu vào cho 039)

| Nguồn | Lấy gì | Không lấy |
|---|---|---|
| antiboredom/camera-motion-detector (OpenCV optical flow, ghi CSV góc, độ lớn, zoom theo khung) | Cách đo máy chạy: tự viết lại trong `tools/style-learn`, ra static/pan/tilt/push/pull, tốc độ và đường cong nhanh dần, chậm dần | Code, nếu giấy phép không rõ |
| dahe-cvl/vhh_cmc (pan/tilt), DGME-T, MovieShots/SGNet, CineScale (cỡ cảnh, góc máy 5 lớp, độ cao máy 6 lớp) | Danh sách nhãn và cách chấm. CineScale có thể dùng để đối chiếu với labeler Opus | Mô hình nặng (Swin, CNN cần GPU CUDA) |
| PySceneDetect (content + adaptive), TransNetV2 (cắt và chuyển cảnh mờ dần) | Phân biệt cắt thẳng, mờ dần, đen: đo độ sáng và chênh lệch khung, theo cách hai ngưỡng | TransNetV2 (cần TensorFlow), trừ khi luật đo đơn giản không đạt |
| inanevin/Cine-AI (MIT, Unity): đặt máy theo idiom của Arijon và luật 180° | Thuật toán đặt máy theo trục hành động: master, OTS, reverse, cận, giữ một phía trục. Viết lại trong `tools/blender/kit/camera.py` | Code C# |
| Leake và cộng sự 2017, "Computational Video Editing for Dialogue-Driven Scenes" | Idiom chọn shot: mở bằng cảnh rộng, người nói trong khung, cận cho câu nặng cảm xúc, nhấn nhân vật. Đếm tần suất từng idiom trên video mẫu | |
| Jiang và cộng sự (SIGGRAPH 2020, 2021), "camera behavior" học từ phim | Ý tưởng: học phân bố tham số máy từ video mẫu rồi áp vào cảnh 3D | Mạng học sâu |
| Netflix "Match Cutting" (arXiv 2210.05766) | Cắt khớp hình: hình dáng hoặc vị trí giống nhau ở hai phía chỗ cắt | |
