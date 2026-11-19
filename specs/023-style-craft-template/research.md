# Research: 023

Phần đã có từ trước (không học lại):
- `references/dusk-hypothetical-3/profile/<v>/frames.csv`: số đo từng khung (dx, dy của máy, độ sáng, bão hoà, cắt, nháy).
- `shots.json`: 2.192 cảnh, nhãn cỡ và góc, ô nét `focus.tiles` (lưới 3×4), `sharpest_at`.
- `shot-sheets/`: một khung mỗi cảnh.
- `analysis/*.md`: ba báo cáo học.

Video và bảng ảnh khung (2 s mỗi bảng) đã bị xoá sau lần học 2026-11-13.

## R1. Tải lại 10 video và giữ đúng mã cảnh cũ

- **Quyết định**: thêm lệnh `learn refetch <set> --videos <URL…>`.
  - Lệnh tải từng URL và ghép với `vNN` cũ theo độ dài (lệch ≤ 1 s). Rồi so 5 khung giữa cảnh với `shot-sheets` (ΔE trung bình ≤ 12) để chắc là đúng video.
  - Ghép xong thì video nằm ở `videos/vNN.mp4`, nên mã cảnh `Sxxx`, nhãn và bằng chứng `bảng#ô` cũ vẫn đúng.
  - Từ nay `set.json` ghi thêm `url` của từng video. Thư mục `references/` không vào git.
- **Danh sách URL**: `set.json` không lưu URL. Lấy danh sách video của kênh bằng yt-dlp (chỉ đọc danh sách, không tải) rồi ghép theo 10 độ dài đã biết (637, 640, 636, 614, 649, 629, 610, 376, 639, 1224 s). Video nào không ghép được một-một thì hỏi người dùng.
- **Vì sao**: giữ được toàn bộ nhãn và bằng chứng cũ; không phải gán nhãn lại (lượt Claude tốn tiền).
- **Đã loại**:
  - Tạo bộ mới `dusk-hypothetical-4`: mất liên kết với 2.192 nhãn, phải gán nhãn lại.
  - Ghép theo `source_sig`: chữ ký này dựa trên kích thước tệp và thời điểm sửa, đổi khi tải lại.

## R2. Đo chuyển động máy và cử động bên trong cảnh

- **Quyết định**: thêm module `tools/style-learn/sl/craft.py` (numpy).
  - Mỗi cảnh: lấy mẫu 12 khung/s, thu về 320×180 xám. Chia lưới khối 16×16; mỗi khối tìm độ dời trong ±8 px. Khớp mô hình máy (dời ngang, dời dọc, phóng) bằng bình phương tối thiểu có loại ngoại lai (2 vòng).
  - **Máy**:
    - tốc độ dời (px/s ở bề ngang 1280) và tốc độ phóng (%/s);
    - loại: `still` (dời < 4 px/s và phóng < 0,5 %/s), `drift-h`, `drift-v`, `push`, `pull`, `follow` (dời đi kèm vùng cử động lớn đi cùng hướng);
    - độ mềm lúc bắt đầu và dừng (thời gian lên tới 80% tốc độ).
  - **Cử động bên trong**: sau khi bù chuyển động máy, khối còn lệch (sai khác > 3σ nhiễu của cảnh) là cử động.
    - Lưu tỉ lệ khối cử động theo thời gian.
    - Đoạn cử động = liền ≥ 2 mẫu vượt ngưỡng; lưu `[t0, t1, độ lớn, tâm]`.
    - Lưu thời gian lên (từ 10% tới 90% độ lớn), lấy làm số cho "tay giơ 0,3–0,6 s rồi giữ".
  - Vùng đồ hoạ (cảnh nhãn `insert`) đo riêng, không tính là diễn xuất.
- **Vì sao**: `frames.csv` chỉ có một độ dời của cả khung (tương quan pha), không tách được phóng, và không biết gì bên trong cảnh. Khớp khối là cách đơn giản nhất cho ra cả máy lẫn phần dư.
- **Đã loại**:
  - OpenCV (luồng quang học): gói nặng, phải thêm vào `CREDITS` và bản lõi đóng gói.
  - Chỉ dùng hiệu khung: lẫn máy trôi với cử động (Edge Cases của spec).
- **Kiểm chứng (SC-003)**: tạo video thử bằng numpy và ffmpeg trong test. Video có hình khối di chuyển biết trước: đứng, trôi ngang, trôi dọc, đẩy vào, kéo ra, một khối "tay" giơ lên trong 0,4 s rồi giữ, và các kiểu chuyển cảnh của R3. Đáp án ghi sẵn. Test đòi đúng ≥ 90% và lệch thời điểm ≤ 0,2 s.

## R3. Loại chuyển cảnh

- **Quyết định**: ở mỗi chỗ đổi cảnh (từ `shots.json`), xét ±0,3 s khung đầy đủ:
  - `streak`: vệt sáng ngang. Có ≥ 2 khung mà hàng sáng (độ sáng hàng > 0,8) chiếm ≥ 15% chiều cao, độ biến thiên dọc theo hàng thấp, kéo dài 0,08–0,25 s.
  - `dip`: nháy đen, độ sáng < 0,03 trong ≥ 2 khung.
  - `fade`: độ sáng đổi đơn điệu trong ≥ 0,15 s rồi lên lại.
  - `wipe`: vật che trượt. Mặt ranh giới hiệu khung chạy ngang hoặc dọc qua khung.
  - Còn lại là `cut`.
  - Dùng lại `motion.events` (nháy, mờ chồng) cho phần đã có.
- **Vì sao**: báo cáo `motion-depth` §2 đã thấy bằng mắt các kiểu này (vệt sáng 0,15 s, nháy đen 0,13 s, mờ dần ≤ 2 lần/phim) nhưng chưa có số đếm và độ dài.

## R4. Diễn xuất: loại động tác

- **Quyết định**:
  - **Số**: thời gian lên, giữ, tần suất đoạn cử động ở cảnh có người. Số lấy từ R2, tự động.
  - **Loại**: chớp mắt, nghiêng đầu, tay giơ, miệng, đi, đổi biểu cảm. Đặt tên bằng mắt: `learn craft` cắt dải 8 khung cho 80 cảnh mẫu (rải đều theo video và cỡ cảnh, chỉ cảnh có người). Claude đọc các dải ngay trong phiên làm việc (như ba báo cáo học) và ghi bảng loại động tác, mỗi dòng có bằng chứng `vNN/strips/Sxxx.jpg#k`.
- **Vì sao**: phân loại động tác tự động đòi mô hình tư thế. Số đo tự động đã đủ cho tầng kiểm; tên động tác chỉ cần cho template và bộ dựng.
- **Đã loại**: một lượt Claude độc lập để gán loại. Việc này tốn tiền mà tầng kiểm không dùng tới.

## R5. Âm thanh: tiếng động, nhạc, mức nhạc so với giọng

- **Quyết định**: thêm `learn sound <set>` (numpy). Dùng mốc từ của `learn transcribe` (faster-whisper, đã có) để biết lúc nào có lời.
  - **Mức nhạc so với giọng**: so RMS trong khoảng nghỉ giữa các từ ≥ 0,25 s với RMS lúc có lời, theo cửa sổ 5 s.
  - **Có nhạc hay không**: trong khoảng nghỉ, năng lượng có cao độ ổn định (độ phẳng phổ < 0,3 trong ≥ 70% khung).
  - **Tiếng động**: điểm bật năng lượng (spectral flux > 4σ) nằm ngoài tiếng nói hoặc vượt nền nhạc > 6 dB; tính số mỗi phút.
  - **Tempo nhạc**: tự tương quan của điểm bật trong các khoảng không lời dài ≥ 4 s. Ghi độ tin cậy thấp khi ít mẫu.
- **Vì sao**: tách nguồn (mô hình học sâu) quá nặng. Khoảng nghỉ của lời là cửa sổ tự nhiên để nghe nền.
- **Đã loại**: tách nguồn bằng mô hình học sâu (gói lớn, chậm, phải ghi giấy phép).

## R6. Nhịp đọc và chia nhịp phim

- **Nhịp đọc**: từ mốc từ, đo
  - số từ/phút theo cửa sổ 10 s và theo nhịp;
  - khoảng nghỉ trong câu, giữa câu, giữa đoạn (đoạn = nghỉ > 0,6 s);
  - khoảng nghỉ ngay trước một từ là số (chữ số hoặc số viết bằng chữ).
- **Chia nhịp**: mỗi video được chia theo 9 nhịp của `STRUCTURE.md`, ghi ở `profile/beats.json`.
  - Claude đọc bản chép lời và đặt ranh giới trong phiên làm việc.
  - Lệnh `learn beats --check` kiểm các nhịp liền nhau và phủ hết video.
  - Mọi số đo theo nhịp gom từ đây.
- **Vì sao**: `STRUCTURE.md` đã có tỉ lệ thời gian của từng nhịp; ghi mốc cho từng video thì mới gom số đo theo nhịp được.

## R7. Sửa chữ bị đọc sai (FR-017)

- **Thực tế**: `core/tts/tts.py` (Kokoro) chỉ đọc trường `text`. Trường `say` chỉ có ở `tts_zh.py`. Không sửa được thư viện (VI).
- **Quyết định**: thêm lệnh `sh bin/studio voice make <phim>`.
  - Lệnh viết `voices/.say.json`, là bản chép `lines.json` với `text` thay bằng `say` nếu dòng đó có `say` (vd. `"say": "hert"`). Rồi gọi `tts.py` của thư viện với tệp này.
  - `lines.json` vẫn giữ `text` đúng kịch bản (`qc` kiểm).
  - `qc voice` so lời nghe được với `asr` (nếu có), rồi với `text`. Từ nào lệch được báo `mispronounced` kèm mã dòng, chữ đúng, chữ nghe được và cách sửa ("thêm `say`").
- **Đã loại**: viết âm vị trực tiếp. `tts.py` không mở đường đưa âm vị vào.

## R8. Định dạng `TEMPLATE.md` và nhãn luật của `STYLE.md`

- **Quyết định**:
  - `TEMPLATE.md` gồm 15 mục cố định (contracts/template-format.md), viết bằng lời của xưởng.
  - Cạnh nó là `template.json`: các khoảng số mà máy đọc được, cho tầng kiểm và bộ dựng.
  - Lệnh `learn template-check <slug>` kiểm:
    - đủ 15 mục;
    - mỗi mục có ≥ 1 số đo kèm khoảng;
    - mỗi mục có ≥ 3 bằng chứng từ ≥ 2 video, hoặc dòng `Ít bằng chứng: n khung`;
    - có "Nên làm", "Không nên làm" và "Trong bộ dựng";
    - 9 công thức nhịp;
    - mỗi luật của `STYLE.md` có `[bằng chứng: …]` hoặc `[xưởng]`.
- **Vì sao**: SC-001, SC-002 đếm được bằng máy; luật thiếu bằng chứng không lọt được nữa.

## R9. Bằng chứng khung hình và bảng so

- **Quyết định**:
  - Khung mẫu nằm trong `references/<set>/profile/<v>/strips/` (dải 8 khung, mỗi khung 320 px) và `evidence/` (khung lẻ 640 px), ngoài git.
  - Bảng so (`learn pairs`) là ảnh lưới: mỗi hàng `khung bộ dựng | khung mẫu`, có tên thành phần và số đo hai bên.
  - Với thành phần có chuyển động, bảng so có thêm một đoạn mp4 ngắn: bên trái là đoạn của bộ dựng, bên phải là dải khung mẫu phát lại đúng nhịp thời gian đã đo. Đoạn này dựng từ ảnh, không cắt từ video mẫu. Đoạn mp4 nằm trong `references/<set>/pairs/` và không gửi đi.
- **Vì sao**: hiến pháp cho giữ "số đo và vài khung hình làm bằng chứng", không giữ video. Video mẫu bị xoá ngay khi học xong (FR-006), trước khi làm bộ dựng, nên phần mẫu của đoạn so phải dựng từ khung đã giữ.
- **Số khung giữ lại**: khoảng 80 dải × 8 khung, cộng các khung lẻ. Ghi ở Complexity Tracking.

## R10. Bố cục, độ sâu, ánh sáng đo từ dữ liệu còn giữ (US1)

US1 không cần tải lại video:
- **Bố cục theo cỡ cảnh**: phân bố ô nét nhất (`sharpest_at` trên lưới 3×4) theo nhãn cỡ, gồm tỉ lệ lệch tâm và tỉ lệ đặt chủ thể ở cột 1/3.
- **Độ sâu theo cỡ cảnh**: `focused_share` theo nhãn cỡ (p25–p75), cùng cờ `foreground_blur` theo cỡ.
- **Ánh sáng**: trên ô của `shot-sheets` (đã biết kích thước ô), đo tỉ lệ điểm sáng ấm (độ sáng > 0,6, sắc độ 20–60°), độ chênh sáng tối (p90 − p10) và hướng gradient độ sáng (nắng xiên).
- **Mặt, áo, đạo cụ, thẻ**: không đo tự động. Mô tả bằng mắt kèm bằng chứng `bảng#ô`; bảng so là nơi người dùng duyệt (FR-013).

## R11. Tầng kiểm chuyển động (FR-011, FR-012, FR-013)

- **Quyết định**: một cách đo duy nhất (`craft.py`), dùng ở ba chỗ:
  1. Bước học (R2).
  2. **Tầng 2, trước khi dựng.** `shots.mjs` chụp thêm 4 khung mỗi cảnh (ở 20%, 40%, 60%, 80% độ dài cảnh, 320×180) vào `.check/shots/motion/`. Python đo phần dư sau khi bù máy.
     - Cảnh có người (theo `window.SHOTS` cùng `window.CAST`, bộ dựng xuất `[[t0, t1, id, số người]]`; trang không xuất thì dùng nhãn của lượt Claude tầng 2) mà phần dư dưới ngưỡng thì báo `still_person`.
     - Ngưỡng = p10 tỉ lệ khối cử động của các cảnh có người ở kênh mẫu, ghi trong `template.json`.
  3. **Tầng 4, trên mp4.** Tính `still_ratio`, `motion720_p50`, tỉ lệ cảnh có người có cử động, độ sâu theo cỡ cảnh. So với khoảng của `template.json`; ngoài khoảng là cảnh báo phong cách (dùng chung `qc accept-style`).
- **Python của tầng kiểm**: `tools/filmcheck` trước giờ chỉ dùng thư viện chuẩn. Phép đo này cần numpy, nên gọi qua `tools/.venv/bin/python` (có numpy, cài bằng `deps learn`). Thiếu venv thì luật báo lỗi "cần `sh bin/studio deps learn`", không âm thầm cho qua. Bản lõi đóng gói của app đã có numpy (bước học dùng).
- **Đã loại**:
  - Đo lại bằng JS trong trang: hai bản cài của cùng một phép đo dễ lệch nhau.
  - Chỉ kiểm sau khi dựng: FR-012 đòi kiểm trước khi dựng.

## R12. Bộ dựng v2 theo template (FR-008)

Giữ hợp đồng của 022 (`film({scenes})`, bảng cảnh, danh mục); thêm trường, không bỏ trường. Bảng cảnh cũ vẫn chạy.

| Thành phần | Thay đổi | Số lấy từ |
|---|---|---|
| Mặt | mắt tròn có đốm sáng, mí cong mảnh, má hồng, miệng nhỏ; chớp mắt tự động (cách nhau theo phân bố đo được, hạt giống theo người); miệng mấp máy khi người đó có bong bóng thoại | R4, khung mẫu |
| Thân áo | hoodie thon có mũ trùm và tay áo; thở (ngực ±1%, chu kỳ 3–4 s) | khung mẫu |
| Diễn xuất | `act: [[thời điểm, động tác], …]` cho từng người; mỗi động tác lên trong thời gian lên đo được (dễ dần) rồi giữ; đi thì di chuyển thật theo `path` | R2, R4 |
| Máy | `move: {type: drift-h\|drift-v\|push\|pull\|follow\|tilt, speed}`; mặc định chọn theo tỉ lệ và tốc độ của cỡ cảnh trong `template.json`; có lúc bắt đầu và dừng mềm | R2 |
| Bố cục | chủ thể đặt theo phân bố ô của cỡ cảnh (lệch tâm, cột 1/3); ECU lệch tâm hoặc cắt một mắt; vật tiền cảnh mờ | R10 |
| Độ sâu | khẩu độ và tiêu điểm theo `focused_share` của cỡ cảnh; đám đông sau mờ thành đốm | R10 |
| Ánh sáng | đèn chính ấm xiên, mảng sáng tối; chỉnh theo bối cảnh | R10 |
| Đạo cụ | mỗi bối cảnh có bộ đạo cụ kể chuyện theo danh mục | khung mẫu |
| Thẻ | `stat` có `icon` (hình ẩn dụ vẽ bằng code); thẻ cuối chữ đậm, biểu tượng lựa chọn, dàn nhân vật 3D thật | khung mẫu |
| Chuyển cảnh | `trans: cut\|streak\|dip\|fade` với độ dài đo được | R3 |
| Âm thanh | `kit/sound/`: tiếng động theo sự kiện từ `events.json`; nhạc tự soạn (`score.py`) bằng sampler của thư viện theo công thức nhạc của từng nhịp (tempo, độ dày, lên, lặng, mức so với giọng) | R5 |
| Nhịp đọc | `kit/timing.py` đọc `template.json` (nghỉ trong câu, giữa câu, giữa đoạn, trước số), thay các hằng số tự đặt như `GAP_IN` trong `build_plan.py` | R6 |

`render(t)` vẫn tất định: chớp mắt và cử động dùng hạt giống của người và thời điểm `t`, không dùng trạng thái giữa hai khung.

## R13. Bản quyền và tên

- Mô tả trong `TEMPLATE.md` viết bằng lời của xưởng, không chép câu thoại.
- Bảng loại động tác chỉ ghi kiểu động tác, không ghi tình tiết.
- `check-names` chạy trên `TEMPLATE.md`, `STYLE.md`, `template.json`, `kit/REVIEW.md` và mọi tệp chữ mới.
- Nhạc tự soạn bằng sampler của thư viện; giấy phép từng bộ nhạc cụ đã nằm trong thư viện. Bộ nhạc cụ nào được dùng thì ghi vào `CREDITS` (CC0, CC BY).
