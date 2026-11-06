---
name: style-learn
description: Học phong cách hình ảnh và âm thanh của một kênh YouTube, một danh sách video, hoặc file video có sẵn, bằng cách đo mọi khung hình; viết thành phong cách 11 mục có bằng chứng, chứng minh bằng một khung vẽ bằng code, rồi lưu vào my-styles/ để làm phim. Dùng khi người dùng nói "học phong cách của kênh…", "clone style video này", "làm phong cách giống kênh…", "learn the style of…".
---

# Học phong cách từ video tham chiếu

Bạn đang ở dự án claude-Utube. Đọc `.specify/memory/constitution.md` nếu chưa đọc trong phiên này: nguyên tắc **VIII (học bằng đo)** và mục **Bản quyền** là luật cứng ở đây. Thiết kế đầy đủ: `specs/002-style-learning/` (spec, research, contracts).

**Ngôn ngữ:**
- Nói với người dùng bằng ngôn ngữ của họ (mặc định tiếng Việt).
- Mọi file phong cách (`STYLE.md`, `EVIDENCE.md`, `style.json`, báo cáo phân tích) viết bằng **tiếng Anh**.

**Chỉ dừng chờ duyệt đúng 2 lần**: bước 6 và bước 8. Ngoài ra chỉ hỏi ở bước 0 khi thiếu thông tin, và câu giữ hay xoá video ở bước 10.

**Luôn nhớ:**
- Không chép câu thoại, tên kênh, tên người, tên nhân vật hay tiêu đề video vào bất kỳ file nào ngoài `references/`.
- Không mở phong cách thư viện nào trước bước 5, để bản phong cách được rút ra từ số đo chứ không từ một phong cách có sẵn.
- Không sửa gì trong `lib/`.
- Mọi lệnh chạy từ gốc dự án. `<set>` là tên bộ (chữ thường, số, gạch nối).

## 0. Hỏi một lần (chỉ khi thiếu)

Gộp vào **một** tin nhắn những gì yêu cầu chưa nói:
- nguồn: link kênh, link video, hay file trên máy;
- số video (mặc định 12, trong khoảng 3–30);
- tên bộ;
- tên cần chặn thêm (tên nhân vật, người dẫn) ngoài tên kênh và tiêu đề.

Những gì không hỏi thì dùng mặc định. Sau đó không hỏi thêm.

## 1. Thu thập và đo

```sh
sh bin/studio deps learn            # lần đầu; thêm --extra nếu cần tải video hoặc chép lời
sh bin/studio learn fetch <set> --channel <URL> --count 12      # hoặc --videos URL… / --files PATH…
sh bin/studio learn measure <set>
sh bin/studio learn transcribe <set>     # cần --extra; nếu không cài được, ghi "chưa có lời" và đi tiếp
sh bin/studio learn summary <set>
```

- `fetch` tự in lời nhắc quyền sử dụng; nhắc lại cho người dùng một dòng.
- Nếu tải bị chặn (mã 1): báo người dùng đặt video vào `references/<set>/videos/`, rồi chạy `fetch <set> --files references/<set>/videos/*`.
- Lỗi khác: đọc thông báo, sửa nguyên nhân, chạy lại. `measure` tự tiếp tục từ chỗ dừng.

## 2. Báo nhanh hồ sơ đo (không dừng)

Từ `references/<set>/profile/summary.md`, báo cho người dùng 3–5 dòng: số video, định dạng chính, vài con số nổi bật.

Nêu cảnh báo nếu có, kèm đề nghị:
- **dưới 5 video**: kết luận kém tin cậy;
- **`dispersion_warnings`**: bộ có thể không đồng nhất; đề nghị chọn nhóm video và đo lại với `--only`;
- **nhiều định dạng** (dọc và ngang lẫn lộn).

## 3. Phân tích bằng 3 agent song song

Gọi **3 agent trong cùng một tin nhắn** (công cụ Agent). Mỗi agent:
- **Chỉ đọc:** `references/<set>/profile/summary.json`, `references/<set>/profile/*/video.json`, ảnh trong `references/<set>/profile/*/sheets/`, và template `.claude/skills/style-learn/templates/aspect-report.md`.
- **Chỉ ghi đúng một file:** `references/<set>/analysis/<group>.md`.

| Agent | `<group>` | Khía cạnh |
|---|---|---|
| 1 | `visual` | màu, viền, ánh sáng, chất liệu, nhân vật |
| 2 | `motion-depth` | chuyển động, chiều sâu |
| 3 | `sound-script` | âm thanh, kịch bản (đọc thêm `profile/*/words.json` nếu có) |

Prompt cho mỗi agent phải có:
1. đường dẫn tuyệt đối tới các file trên;
2. yêu cầu xem **ít nhất 3 bảng ảnh của mỗi video**: đầu, giữa, cuối; với chuyển động thì xem thêm các bảng quanh mỗi lần cắt;
3. mỗi kết luận theo dạng `Claim · Evidence · Confidence` của template;
4. luật bản quyền ở đầu file này;
5. phụ đề hay chữ cháy vào hình của kênh **không** phải chữ của phong cách, trừ khi người dùng đã xác nhận;
6. agent `sound-script`: kịch bản chỉ ghi **cấu trúc** (kiểu câu mở đầu, số nhịp leo thang, kiểu cụm chuyển ý, kiểu kết, tốc độ đọc). Không ghi câu nào, kể cả một câu ngắn.

## 4. Kiểm tra chéo

Đọc 3 báo cáo. Với **mỗi** kết luận:
- So với con số tương ứng trong `summary.json` hoặc `video.json`.
- Mở đúng ảnh và ô được dẫn để tự xem.
- Kết luận sai hoặc nói quá thì sửa. Ghi mọi chỗ sửa vào `references/<set>/analysis/corrections.md` theo template `corrections.md`.
- Hai agent mâu thuẫn nhau: xem số đo và ảnh để quyết.

Các lỗi đã từng gặp (từ claude-animated-shorts), cần kiểm riêng:
- "Camera đứng yên phần lớn thời gian" có thể sai: xem `motion720_p50` và `still_ratio`; pan chậm vẫn là chuyển động.
- "Nhiều cắt cảnh" có thể thật ra là chớp sáng: xem `flashes_per_min` so với `cuts_per_min`.
- Nhận xét về hình dáng (ví dụ đầu "hình trứng") phải đo trên ít nhất 10 khung, không đoán qua một khung.

## 5. Viết bản phong cách

1. **Chọn `based_on`:** phong cách thư viện có **kỹ thuật** gần nhất (2D Canvas, nét cọ, 3D three.js…). Đọc `lib/lemo-opuscar/styles/README.md` rồi chỉ đọc `STYLE.md` của 2–3 ứng viên. Lấy kỹ thuật dựng (engine), **không lấy luật**.
2. **Viết `references/<set>/style/STYLE.md`** theo đúng 11 mục của `lib/lemo-opuscar/styles/_template/STYLE.md` (đọc template đó, kể cả phần hướng dẫn trong comment):
   - mỗi luật kèm `(evidence: …)` trỏ tới số đo hoặc `sheet#ô`;
   - chỉ ghi những gì đúng cho **mọi** phim theo phong cách này; không ghi câu chuyện;
   - mục 10 (Engine) mô tả cách dựng bằng bộ máy `render(t)` dựa trên `based_on`;
   - mục 11 gợi ý cấu trúc, cách mở đầu và cách kết **khác** kênh gốc.
3. **Viết `references/<set>/style/EVIDENCE.md`:** tóm tắt 3 báo cáo cùng nhật ký sửa, và lý do chọn `based_on`.
4. **Viết `references/<set>/style/style.json`:** `{"line": "<một câu tiếng Anh>", "line_cn": "", "borrows": [], "size": "<WxH nếu không phải 1920x1080>"}`.
5. Chạy kiểm tra tên:
   ```sh
   sh bin/studio learn check-names <set> references/<set>/style/STYLE.md references/<set>/style/EVIDENCE.md references/<set>/style/style.json
   ```
   Mã 1 thì sửa và chạy lại cho tới khi đạt.

## 6. ⏸ Duyệt lần 1

Viết bản tóm tắt theo `.claude/skills/style-learn/templates/review-vi.md`, gửi người dùng và **dừng chờ**.
- Có góp ý: sửa `STYLE.md` (ghi lại thay đổi trong `EVIDENCE.md`), chạy lại `check-names`, rồi trình lại.
- Người dùng đồng ý: sang bước 7.

## 7. Khung chứng minh

1. **Chọn khung gốc:** khung có độ sáng, bão hoà, độ tối gần trung vị của bộ nhất (xem `frames.csv`), trong một cảnh tiêu biểu. Nếu người dùng muốn chọn thì cho họ chọn. Trích khung đó:
   ```sh
   ffmpeg -v error -y -ss <t> -i references/<set>/videos/<file> -frames:v 1 references/<set>/proof/out/ref.jpg
   ```
   Khung gốc **chỉ** nằm trong `proof/out/` (không bị lưu vào phong cách).
2. **Viết `references/<set>/proof/index.html`** theo hợp đồng trang của thư viện:
   - có `window.render(t)`, `window.READY`, `window.DUR`;
   - nạp thư viện bằng URL tuyệt đối như `/core/lib.js` (xem `lib/lemo-opuscar/TECHNIQUE.md` §2);
   - kích thước = kích thước video gốc;
   - vẽ một cảnh **mới** theo `STYLE.md`: cùng ánh sáng, màu, viền, bố cục kiểu kênh, nhưng nhân vật và vật thể là của mình.
3. **Chụp** (cần `sh bin/studio deps` một lần cho thư viện):
   ```sh
   LIB="$PWD/lib/lemo-opuscar"; P="$PWD/references/<set>/proof"
   (cd "$LIB" && node core/render/still.mjs "$P" 0 --size <W>x<H> --out "$P/out" --prefix ours_r1_)
   sh bin/studio learn compare <set> --ref "$P/out/ref.jpg" --ours "$P/out/ours_r1_0.jpg" --round 1
   ```
4. **Chưa đạt:** sửa trang theo chỉ số lệch, chụp lại với `--prefix ours_r2_` và `--round 2`, rồi `ours_r3_` và `--round 3`. Tối đa **2 vòng sửa**.
5. **Không chạy được `node`** hoặc `deps` của thư viện: dừng ở đây, báo rõ cho người dùng (bản nháp phong cách vẫn còn trong `references/<set>/style/`), và nói cách chạy tiếp trên máy của họ.

## 8. ⏸ Duyệt lần 2

Gửi người dùng (bằng ngôn ngữ của họ):
- ảnh `references/<set>/proof/compare.jpg` (gốc bên trái, tự vẽ bên phải);
- bảng 4 chỉ số kèm ngưỡng;
- nếu chưa đạt: chỉ số nào chưa đạt và vì sao.

Rồi **dừng chờ**. Người dùng chấp nhận một khung chưa đạt thì bước 9 thêm `--accept-proof`.

## 9. Lưu

Chọn `slug` và tên tiếng Anh (cùng tên tiếng Trung nếu người dùng muốn). Không được chứa tên kênh hay tên người.

```sh
sh bin/studio learn save <set> --slug <slug> --en "<English Name>" [--cn "<中文名>"] --based-on <based_on> [--accept-proof]
```

Lệnh tự chặn: slug trùng, tên kênh, media hay bản chép lời trong gói. Lỗi thì sửa theo thông báo rồi chạy lại.

## 10. Giữ hay xoá video tham chiếu

Hỏi đúng một câu: *"Giữ video tham chiếu của bộ <set> trên máy không? Mặc định là xoá; số liệu đo vẫn được giữ."*

```sh
sh bin/studio learn clean <set>          # mặc định, hoặc khi người dùng không trả lời rõ
sh bin/studio learn clean <set> --keep   # chỉ khi người dùng nói giữ
```

Cuối cùng báo cho người dùng:
- phong cách nằm ở `my-styles/<slug>/` và đã có trong danh mục `my-styles/README.md`;
- cách dùng: *"Làm phim 30 giây theo phong cách <tên> về …"*;
- nhắc commit `my-styles/<slug>/` nếu họ muốn lưu lên git.
