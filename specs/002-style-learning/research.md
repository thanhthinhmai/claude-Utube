# Research: Học phong cách từ video tham chiếu

## 1. Tải video và chọn tiếng gốc

- **Decision**: Dùng `yt-dlp` (gói Python, tuỳ chọn). Kênh: lấy tab theo link người dùng đưa (`/videos`, `/shorts`, hoặc trang kênh), `--playlist-end N` (mặc định 12). Định dạng: video ≤ 720p kèm audio, để `yt-dlp` sắp xếp theo mặc định (ưu tiên tiếng gốc khi video có nhiều bản lồng tiếng). Ghi `--write-info-json`; lưu `language` của audio đã chọn vào `set.json`.
- **Rationale**: 720p là đủ vì đo ở rộng 320 px, và ảnh trong bảng ảnh nhỏ hơn nữa. Info JSON cho biết tên kênh và tiêu đề, là đầu vào cho `check-names`.
- **Cần kiểm chứng khi code**: việc chọn tiếng gốc với video có lồng tiếng tự động. Nếu info JSON không đánh dấu được bản gốc thì ghi `audio_language: "unknown"` (Acceptance US1-3).
- **Alternatives considered**: Gọi API của nền tảng (cần khoá, không tải được media); để người dùng tự tải (vẫn hỗ trợ qua `fetch --files`).

## 2. Phần được đo

- **Decision**: Video ≤ 180 s đo toàn bộ. Video > 180 s đo 60 s đầu, cộng 4 đoạn 30 s đặt cách đều trong phần còn lại (tâm đoạn ở 1/5, 2/5, 3/5, 4/5 phần còn lại). Tổng cộng 180 s; đổi được bằng `--max-seconds`.
- **Rationale**: Đúng câu trả lời Q2-B. Phần mở đầu chứa hook và cách giới thiệu, các đoạn rải đều bắt được nhịp giữa video.

## 3. Giải mã khung

- **Decision**: `ffmpeg -ss a -t d -i file -vf scale=320:-2:flags=area,format=rgb24 -f rawvideo -` đọc qua pipe, mỗi khung là một mảng numpy `H×320×3`. Số khung mong đợi lấy từ `ffprobe` (`nb_frames` hoặc `duration × fps`); SC-001 so số khung đọc được với số này (sai số ±1 khung mỗi đoạn do làm tròn).
- **Rationale**: 320 px giữ đủ cấu trúc để đo chuyển động và màu, và nhanh (~0,2 MB mỗi khung). Video dọc cho ra 320×568.
- **Alternatives considered**: PyAV (thêm phụ thuộc biên dịch); OpenCV `VideoCapture` (nặng, khó đọc đúng số khung).

## 4. Chuyển động camera

- **Decision**: Phase correlation trên ảnh xám đã nhân cửa sổ Hann. Lấy đỉnh của `IFFT(F1·conj(F2)/|F1·conj(F2)|)`, nội suy dưới điểm ảnh theo Foroosh et al. (2002). Khi code đã đo: nội suy parabol đo pan 0,13 px/khung thành 0,058 px (thiếu 57%), Foroosh đo 0,150 px (sai 12%). Chuẩn hoá: `motion = hypot(dx, dy) / W` (tỷ lệ chiều rộng mỗi khung), và quy ra điểm ảnh ở 720p để so với số liệu của claude-animated-shorts. **Đứng yên** khi `motion·720 < 0,5`. Độ tin cậy là độ cao đỉnh; dưới 0,05 thì đánh dấu `motion_ok=false` (khung có cảnh chuyển động phức tạp).
- **Rationale**: Dùng numpy FFT là đủ, không cần OpenCV. Có ghi chú về bài học "camera di chuyển chậm 65% thời gian": ngưỡng 0,5 px phải được kiểm bằng video pan chậm (test pan 0,3 px/khung và 2 px/khung).
- **Giới hạn đã biết**: không đo zoom hay xoay. Báo cáo ghi rõ; nhóm agent chuyển động kiểm bằng mắt.

## 5. Cắt cảnh

- **Decision**: Histogram 3 kênh × 16 bin, khoảng cách L1 chuẩn hoá về 0–1 giữa hai khung liên tiếp. Là **cắt cảnh** khi `d > max(0,4, 8 × trung vị cửa sổ 1 giây)` **và** khung sau đó vẫn khác khung trước cắt (`d(f-1, f+2) > 0,4`). Là **chớp sáng** (flash) khi độ sáng nhảy lên rồi trở lại trong ≤ 6 khung: ghi riêng, không tính cắt.
- **Rationale**: Bài học từ claude-animated-shorts: nhiều "cắt" thực ra là chớp sáng 4 khung. Điều kiện thứ hai loại khung lỗi một khung.
- **Kiểm chứng**: SC-002 (≥ 95% đúng, ≤ 5% báo nhầm) trên video tổng hợp có 5 cắt cứng, 1 chớp sáng, 1 hoà tan (dissolve) 12 khung; hoà tan được ghi là chuyển cảnh mềm và không tính là cắt.

## 6. Màu

- **Decision**: Mỗi khung tính: luma Rec.709 (0–1) trung bình; tương phản = độ lệch chuẩn luma; bão hoà HSV trung vị; `dark% = luma < 0,06`, `bright% = luma > 0,94`. Bảng màu: lấy mẫu mỗi 10 khung, 400 điểm ảnh mỗi khung, chuyển sang Lab (D65), k-means k = 8 (seed cố định, 25 vòng). Gộp các cụm gần như trùng nhau (ΔE76 < 5); bỏ cụm < 1% điểm ảnh (nhiễu nén ở mép màu, đo thấy 0,2–0,4% trên video 3 dải màu). Báo hex và tỷ lệ của **6 cụm lớn nhất** (luôn đủ 6 trừ khi chỉ còn ít hơn 6 cụm sau khi gộp; khi đó ghi `palette_note`).
- **SC-004, so màu gần**: khoảng cách ΔE76 < 15 giữa cặp màu ghép theo kiểu tham lam (greedy).
- **Rationale**: Lab cho khoảng cách màu gần với mắt người; k-means tự viết dài khoảng 30 dòng.

## 7. Âm thanh

- **Decision**:
  - Độ lớn: `ffmpeg -af ebur128` trên phần được đo, đọc `I:` (LUFS) và `LRA:`.
  - Khoảng lặng: giải mã mono 16 kHz, RMS cửa sổ 50 ms; im lặng khi < −45 dBFS liên tục ≥ 250 ms; báo tổng thời gian và số lần.
  - Thời điểm lời đầu tiên: từ đầu tiên trong `words.json`, hoặc nếu không có thì khoảng lặng đầu tiên kết thúc.
- **Rationale**: Đúng các chỉ số trong style bible (−14 LUFS, LRA ~2,4, khoảng lặng < 1 s mỗi video).

## 8. Chép lời và tốc độ đọc

- **Decision**: `faster-whisper` (tuỳ chọn), `word_timestamps=True`, tự nhận ngôn ngữ. Mô hình mặc định `small` (đa ngữ); đổi bằng `--model`. Tốc độ đọc = số từ ÷ (thời gian từ đầu tới từ cuối − tổng khoảng ngắt > 0,25 s). Với ngôn ngữ không tách từ bằng dấu cách (tiếng Trung, Nhật), đếm ký tự và ghi đơn vị `chars/s`.
- **Rationale**: Thư viện đã dùng faster-whisper; bài học từ claude-animated-shorts là tự chép lời bản gốc. Tách hàm tính tốc độ khỏi phần chép lời để test được bằng `words.json` giả.
- **Khi thiếu `faster-whisper`**: bỏ qua bước này, ghi `speech: null`, và phần kịch bản trong báo cáo ghi "chưa có lời".

## 9. Bảng ảnh

- **Decision**: Mỗi 2 giây của phần được đo thành một ảnh ghép đủ mọi khung (30 fps → 60 khung → lưới 10×6), ô rộng 128 px (ngang) hoặc 72 px (dọc); dán nhãn thời gian góc trái trên. Lưu JPEG chất lượng 80.
- **Rationale**: Đúng FR-009 và phương pháp gốc ("mỗi 2 giây một ảnh, 60 khung"). Ảnh này cho phép agent nhìn được mọi khung.

## 10. Phân tích bằng 3 agent

- **Decision**: Skill gọi 3 agent song song (công cụ Agent). Mỗi agent nhận: đường dẫn `summary.json`, `video.json` của các video, thư mục bảng ảnh, và template `aspect-report.md`. Mỗi agent chỉ ghi `analysis/<group>.md`:
  - `visual`: màu, viền, ánh sáng, chất liệu, nhân vật
  - `motion-depth`: chuyển động, chiều sâu
  - `sound-script`: âm thanh, kịch bản

  Mỗi kết luận có dạng `Claim · Evidence (số đo hoặc file:khung) · Confidence`. Sau đó agent chính kiểm tra chéo (FR-013) và ghi `analysis/corrections.md`.
- **Rationale**: Theo câu trả lời Q-agent: 3 nhóm. Tách file để agent không ghi đè nhau (bài học "chia file, không chỉ chia việc").

## 11. Khung chứng minh

- **Decision**:
  1. Người dùng (hoặc skill, nếu người dùng để skill quyết) chọn **một khung gốc tiêu biểu** từ bảng ảnh: khung gần trung vị của nhiều chỉ số nhất.
  2. Claude viết `references/<set>/proof/index.html` theo hợp đồng `render(t)`, dùng `/core/lib.js` của thư viện. Kích thước bằng tỷ lệ khung gốc (`--size`).
  3. Chụp bằng `cd $LIB && node core/render/still.mjs <proof> 0 --size WxH --out <proof>/out`.
  4. `learn compare` tính bảng chênh lệch SC-004 và ghép ảnh trái–phải.
- **Rationale**: Đúng bộ máy đã chốt (VII) và không sửa thư viện (VI). Thư viện tự mount thư mục ngoài ở `/@film/` (`core/render/serve.mjs`).

## 12. Chặn tên và câu thoại (`check-names`)

- **Decision**:
  - Danh sách cấm = tên kênh, uploader, `@handle` và tiêu đề video từ info JSON, cộng tên do người dùng thêm (`--deny`).
  - Báo lỗi khi file phong cách chứa một mục cấm (không phân biệt hoa thường, so cả bản bỏ dấu), hoặc chứa **chuỗi 6 từ liên tiếp** có trong bất kỳ bản chép lời nào.
  - Tên kênh từ 3 từ trở lên: chặn thêm mọi cụm 2 từ liền nhau (trừ cụm chỉ gồm từ chung như studio, official, tv), để "Mèo Lười Night" cũng bị chặn khi kênh là "Mèo Lười Studio".
  - Tên riêng trong bản chép lời: từ viết hoa không ở đầu câu, lặp từ 2 lần trở lên, cũng bị chặn (tên người dẫn, nhân vật).
  - Mã thoát 1 kèm vị trí. `save` gọi lại bước này và từ chối nếu lỗi.
- **Rationale**: SC-003 đòi 0 tên và 0 câu thoại nguyên văn. Chuỗi 6 từ đủ dài để không bắt nhầm cụm thông dụng.

## 13. Gói phong cách đã lưu

- **Decision**: `my-styles/<slug>/` theo định dạng `MY-STYLES.md` của thư viện, điều chỉnh cho phong cách học được:

| File | Nội dung |
|---|---|
| `STYLE.md` | 11 mục, tiếng Anh, mỗi luật có `(evidence: …)` |
| `style.json` | `slug`, `en`, `cn`, `based_on` (phong cách thư viện gần nhất về kỹ thuật, dùng cho engine), `borrows: []`, `size`, `library_version`, `created`, `line`, `line_cn`, `source: "learned"`, `reference: {videos, measured_seconds, formats}` (không có tên kênh) |
| `EVIDENCE.md` | Tóm tắt 3 báo cáo nhóm cùng nhật ký sửa, tiếng Anh |
| `measurements/summary.json` | Số liệu tổng hợp (không có tiêu đề, không có id video) |
| `styleframe/` | `index.html` cùng file nguồn nhỏ của khung chứng minh |
| `styleframe.jpg` | Khung tự vẽ đã duyệt |

  `styleframe/` chỉ nhận mã nguồn dạng chữ và font; ảnh raster trong `proof/` (ngoài `out/`) làm `save` từ chối, vì có thể là khung của video gốc.
  **Không lưu**: video, âm thanh, bản chép lời, bảng ảnh, ảnh ghép có khung gốc. Những thứ này ở lại `references/<set>/` (mặc định bị xoá ở bước cuối).
- **Rationale**: SC-006, FR-015, FR-020; luồng làm phim của 001 đọc `my-styles/README.md` như danh mục `~/lemo-my-styles/README.md` của thư viện.
- **`based_on`**: thư viện yêu cầu mỗi phong cách riêng có kỹ thuật gốc. Skill chọn phong cách thư viện có engine gần nhất (ví dụ phong cách 2D vẽ bằng Canvas, hay phong cách 3D) và ghi lý do vào `EVIDENCE.md`.

## 14. Môi trường Python riêng

- **Decision**: `sh bin/studio deps learn` tạo `tools/.venv` (bằng `uv venv` nếu có, không thì `python3 -m venv`), cài `requirements-learn.txt`. Thêm `--extra` để cài `requirements-learn-extra.txt` (yt-dlp, faster-whisper). Đánh dấu bằng checksum như `setup.sh` của thư viện, để chạy lại thì không cài lại.
- **Rationale**: Hiến pháp VI và TECHNIQUE.md §1 của thư viện cấm cài vào `$LIB/.venv`. Tách phần nặng (faster-whisper khoảng 0,5 GB cùng mô hình) thành tuỳ chọn.
