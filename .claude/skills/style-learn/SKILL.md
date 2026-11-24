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

**Giao diện và sổ việc** (tính năng 003, `specs/003-studio-ui/contracts/skill-integration.md`):
- Mọi bước dưới đây đều ghi vào sổ việc bằng `sh bin/studio job …`, để người dùng theo dõi trên giao diện web. Hai lần duyệt đi qua `sh bin/studio review …`, để người dùng bấm nút trên giao diện.
- Nếu `sh bin/studio job start` báo chưa cài giao diện (mã 1), **không dừng**: bỏ qua mọi lệnh `job` và `review`, và duyệt trong khung chat như cũ. Gợi ý người dùng một lần: `sh bin/studio deps ui`.
- Lưu mã việc vào biến `JOB` ở bước 0 và dùng lại; nếu shell đổi, đọc lại từ `references/<set>/style/.job`.

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

Khi đã có tên bộ, mở việc và **in đường link giao diện cho người dùng**:

```sh
mkdir -p references/<set>/style
sh bin/studio job start --kind learn --name <set> --set <set> | tee references/<set>/style/.job.out
JOB=$(head -1 references/<set>/style/.job.out); echo "$JOB" > references/<set>/style/.job
```

Báo người dùng dòng `URL: …` mà lệnh in ra: *"Theo dõi và duyệt trên giao diện: <URL>"*.

## 1. Thu thập và đo

```sh
sh bin/studio deps learn            # lần đầu; thêm --extra nếu cần tải video hoặc chép lời
sh bin/studio job run $JOB --step "Fetch videos" -- sh bin/studio learn fetch <set> --channel <URL> --count 12   # hoặc --videos / --files
sh bin/studio job run $JOB --step "Measure videos" -- sh bin/studio learn measure <set>
sh bin/studio job run $JOB --step "Transcribe" -- sh bin/studio learn transcribe <set>   # cần --extra; không cài được thì ghi "chưa có lời"
sh bin/studio job run $JOB --step "Summarize" -- sh bin/studio learn summary <set>
```

`job run` giữ nguyên đầu ra và mã thoát của lệnh bên trong, và gửi nhịp sống mỗi 30 giây để việc không bị coi là "không còn hoạt động".

- `fetch` tự in lời nhắc quyền sử dụng; nhắc lại cho người dùng một dòng.
- Nếu tải bị chặn (mã 1): báo người dùng đặt video vào `references/<set>/videos/`, rồi chạy `fetch <set> --files references/<set>/videos/*`.
- Lỗi khác: đọc thông báo, sửa nguyên nhân, chạy lại. `measure` tự tiếp tục từ chỗ dừng.

### 1b. Cách quay: cỡ cảnh, góc máy, độ nét, bối cảnh (specs/021)

Chạy khi video còn trên máy, trước `summary`:

```sh
sh bin/studio job run $JOB --step "Shots" -- sh bin/studio learn shots <set>       # tách cảnh, khung giữa cảnh, độ nét
sh bin/studio job run $JOB --step "Label shots" -- sh bin/studio learn label <set>  # một lượt Claude Opus độc lập mỗi video
sh bin/studio learn label <set> --pass 2 --sample 40                                # lượt thứ hai, đo độ nhất quán
```

- Video nào in `!` (số cắt mỗi phút lạ): mở bảng ảnh `profile/<vid>/shot-sheets/` và xem có cắt giả không.
- Cảnh in `!` (nhãn mâu thuẫn với số đo độ nét): mở đúng ô trên bảng ảnh; nhãn sai thì sửa bằng
  `sh bin/studio learn label <set> --set 'vNN:Sxxx scale=… angle=… place=…'`.
- Báo người dùng độ nhất quán (`profile/agreement.json`): cùng cỡ cảnh, lệch không quá một bậc, cùng góc máy.
- Bảng ảnh có nhãn và nhãn được giữ lại sau `clean`; khung cỡ lớn thì bị xoá.

### 1c. Tay nghề theo thời gian: máy, cử động, chuyển cảnh, âm thanh (specs/023)

Số trung bình của từng khung không cho biết máy đẩy vào hay nhân vật có diễn không. Chạy khi video còn trên máy, sau `transcribe` và `shots`:

```sh
sh bin/studio job run $JOB --step "Craft" -- sh bin/studio learn craft <set> --strips 80   # máy (dời, phóng, bám), cử động sau khi bù máy, chuyển cảnh; 80 dải khung
sh bin/studio job run $JOB --step "Sound" -- sh bin/studio learn sound <set>              # nhịp đọc, nhạc trong khoảng nghỉ, tiếng động, tempo
sh bin/studio learn evidence <set> <vNN> <giây> --name <tên>                             # khung lẻ 640 px làm bằng chứng (máy, âm thanh, nhịp đọc)
```

- Xem dải khung (`profile/<v>/strips/`) bằng mắt và ghi bảng loại động tác (đổi nét mặt, động tác tay, đạo cụ tự diễn, đồ hoạ dựng lên…), mỗi dòng có bằng chứng `vNN/strips/Sxxx.jpg#k`.
- `still_ratio` cũ chỉ thấy máy dời; số máy đứng thật (không dời, không phóng) lấy từ `craft-summary.json → motion`.
- Diễn xuất chỉ đọc trên cảnh máy đứng: máy đi trong cảnh 3D để lại phần dư do thị sai.
- Tempo có độ tin cậy thấp thì ghi như gợi ý; số tiếng động là mức trần (có lẫn phách nhạc).
- Đo xong thì xoá video ngay (bước 10), trước khi làm bộ dựng; dải khung và khung bằng chứng được giữ.
- Học thêm một bộ đã xoá video: `sh bin/studio learn refetch <set> --videos <URL…>` tải lại vào đúng `vNN` cũ (ghép theo độ dài và khung giữa cảnh), nên nhãn và bằng chứng cũ vẫn dùng được; `transcribe` chép lời lại cho video đã mất `words.json`.

## 2. Báo nhanh hồ sơ đo (không dừng)

`sh bin/studio job step $JOB "Report measurements"` ở đầu bước.

Từ `references/<set>/profile/summary.md`, báo cho người dùng 3–5 dòng: số video, định dạng chính, vài con số nổi bật.

Nêu cảnh báo nếu có, kèm đề nghị:
- **dưới 5 video**: kết luận kém tin cậy;
- **`dispersion_warnings`**: bộ có thể không đồng nhất; đề nghị chọn nhóm video và đo lại với `--only`;
- **nhiều định dạng** (dọc và ngang lẫn lộn).

## 3. Phân tích bằng 3 agent song song

`sh bin/studio job step $JOB "Analysis (3 agents)"` ở đầu bước.

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

`sh bin/studio job step $JOB "Cross-check"` ở đầu bước.

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

`sh bin/studio job step $JOB "Write style"` ở đầu bước.

1. **Chọn `based_on`:** phong cách thư viện có **kỹ thuật** gần nhất (2D Canvas, nét cọ, 3D three.js…). Đọc `lib/lemo-opuscar/styles/README.md` rồi chỉ đọc `STYLE.md` của 2–3 ứng viên. Lấy kỹ thuật dựng (engine), **không lấy luật**.
2. **Viết `references/<set>/style/STYLE.md`** theo đúng 11 mục của `lib/lemo-opuscar/styles/_template/STYLE.md` (đọc template đó, kể cả phần hướng dẫn trong comment):
   - mỗi luật kèm `(evidence: …)` trỏ tới số đo hoặc `sheet#ô`;
   - mục 6 (Camera grammar) và phần chiều sâu ở mục 2 ghi **bằng số** từ mục "Shot grammar" của `summary.md`: tỉ lệ từng cỡ cảnh và góc máy, tỉ lệ đổi cỡ giữa hai cảnh liền nhau, chuỗi cùng cỡ dài nhất, phần khung nét, bối cảnh; thêm các hàng đó vào "Key numbers" của `EVIDENCE.md`;
   - chỉ ghi những gì đúng cho **mọi** phim theo phong cách này; không ghi câu chuyện;
   - mục 10 (Engine) mô tả cách dựng bằng bộ máy `render(t)` dựa trên `based_on`;
   - mục 11 (cấu trúc phim), specs/022: xem kênh mà phong cách được học cho (`sh bin/studio channel show <kênh>`):
     - kênh có quyết định **theo cấu trúc của kênh tham chiếu**: viết thêm `references/<set>/style/STRUCTURE.md` gồm các màn, tỉ lệ thời lượng, mốc chuyển, nhịp leo thang (đo từ bản chép lời và bảng cảnh), **không** câu chữ, nhân vật, câu chuyện hay tên nào của kênh tham chiếu; mục 11 trỏ tới `STRUCTURE.md`;
     - kênh không có quyết định đó, hoặc chưa gắn kênh: mục 11 gợi ý cấu trúc, cách mở đầu và cách kết **khác** kênh gốc (luật cũ), không viết `STRUCTURE.md`.
   Mỗi luật (dòng bảng hoặc gạch đầu dòng ở mục 1–11) mang `[bằng chứng: <bảng#ô | tệp → khoá | báo cáo §n.m>]` hoặc `[xưởng]` (luật xưởng tự chọn, ví dụ phụ đề in trên hình). Luật không có bằng chứng và không phải của xưởng thì bỏ, ghi vào nhật ký sửa (specs/023 FR-001).
3. **Viết `references/<set>/style/EVIDENCE.md`:** tóm tắt 3 báo cáo cùng nhật ký sửa, và lý do chọn `based_on`.
4. **Viết `references/<set>/style/style.json`:** `{"line": "<một câu tiếng Anh>", "line_cn": "", "borrows": [], "size": "<WxH nếu không phải 1920x1080>"}`.
5. **Template tay nghề (specs/023):**
   - chia nhịp từng video theo `STRUCTURE.md` vào `profile/beats.json`, rồi `sh bin/studio learn beats <set> --check`;
   - `sh bin/studio learn craft-summary <set> --parts look time`;
   - viết `TEMPLATE.md` (15 thành phần, 9 công thức nhịp) và `template.json` theo `specs/023-style-craft-template/contracts/template-format.md`, bằng lời của xưởng; mỗi thành phần ≥ 1 số đo kèm khoảng và ≥ 3 khung mẫu từ ≥ 2 video (hoặc "Ít bằng chứng: n khung");
   - `sh bin/studio learn template-check <slug>` sau khi lưu (bước 9); trước đó có thể kiểm phần hình bằng `--partial 1-10`.
6. Chạy kiểm tra tên:
   ```sh
   sh bin/studio learn check-names <set> references/<set>/style/STYLE.md references/<set>/style/EVIDENCE.md references/<set>/style/style.json [references/<set>/style/STRUCTURE.md]
   ```
   Mã 1 thì sửa và chạy lại cho tới khi đạt.

## 6. ⏸ Duyệt lần 1

Viết bản tóm tắt theo `.claude/skills/style-learn/templates/review-vi.md` vào `references/<set>/style/review-1.md`, rồi gửi yêu cầu duyệt:

```sh
sh bin/studio review request $JOB --kind style-1 --set <set> --summary references/<set>/style/review-1.md
```

Lệnh in mã duyệt (dòng 1, gọi là `RID`) và `URL: …`. Gửi người dùng **cùng bản tóm tắt** trong khung chat, kèm: *"Duyệt trên giao diện: <URL>. Hoặc bấm Esc rồi trả lời ở đây."* Rồi **chờ**:

```sh
sh bin/studio review wait $RID        # chặn tới 9 phút; mã 3 = chưa có quyết định → chạy lại đúng lệnh này
```

- Mã 0: lệnh in JSON quyết định `{value, note, source}`. Làm theo `value`.
- Người dùng bấm Esc và trả lời trong khung chat: ghi lại bằng `sh bin/studio review decide $RID --value approve|revise --note "<góp ý>" --source chat` rồi làm theo. Mã 4 = đã có quyết định trên giao diện: đọc bằng `sh bin/studio review status $RID` và theo quyết định đó.
- `revise`: sửa `STYLE.md` theo `note` (ghi lại thay đổi trong `EVIDENCE.md`), chạy lại `check-names`, viết lại `review-1.md`, rồi gửi một yêu cầu **mới** `style-1` và chờ lại.
- `approve`: sang bước 7.

## 7. Khung chứng minh

`sh bin/studio job step $JOB "Proof frame round <n>"` ở mỗi vòng.

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
   Rồi một **đoạn video ngắn** (3–10 s) của trang chứng minh có máy và cử động, so cả số đo chuyển động (specs/023 FR-007):
   ```sh
   (cd "$LIB" && node core/render/still.mjs "$P" --range 0:6:0.0333 --out "$P/out/clip" --prefix c_ --size <W>x<H>)
   ffmpeg -framerate 30 -pattern_type glob -i "$P/out/clip/c_*.jpg" -pix_fmt yuv420p "$P/out/clip.mp4"
   sh bin/studio learn compare <set> --clip "$P/out/clip.mp4"      # máy đứng, motion720, phần có cử động so với kênh mẫu
   ```
4. **Chưa đạt:** sửa trang theo chỉ số lệch, chụp lại với `--prefix ours_r2_` và `--round 2`, rồi `ours_r3_` và `--round 3`. Tối đa **2 vòng sửa**.
5. **Không chạy được `node`** hoặc `deps` của thư viện: dừng ở đây, báo rõ cho người dùng (bản nháp phong cách vẫn còn trong `references/<set>/style/`), và nói cách chạy tiếp trên máy của họ.

## 8. ⏸ Duyệt lần 2

Viết vào `references/<set>/style/review-2.md` (ngôn ngữ của người dùng): ghi chú về những gì số đo **không** bắt được (bố cục, dáng nhân vật, chữ trên màn hình…), và nếu chưa đạt thì chỉ số nào chưa đạt và vì sao. Rồi gửi yêu cầu duyệt; thêm `--final-round` khi đã dùng hết 2 vòng sửa mà chưa đạt:

```sh
sh bin/studio review request $JOB --kind style-2 --set <set> --summary references/<set>/style/review-2.md [--final-round]
sh bin/studio review wait $RID        # như bước 6
```

Giao diện tự hiện ảnh gốc và ảnh tự vẽ cạnh nhau cùng bảng 4 chỉ số (từ `proof/compare.json`). Trong khung chat, gửi người dùng URL, bảng 4 chỉ số và đường dẫn `references/<set>/proof/compare.jpg`.

- `approve`: sang bước 9.
- `revise`: sửa trang theo `note`, chụp lại (vẫn tính trong giới hạn 2 vòng sửa), gửi yêu cầu `style-2` mới.
- `accept_anyway` (chỉ có khi `--final-round`): bước 9 thêm `--accept-proof`.
- `stop`: `sh bin/studio job stop $JOB`, báo người dùng bản nháp còn ở `references/<set>/style/`, và dừng.

## 9. Lưu

`sh bin/studio job step $JOB "Save style"`.

Chọn `slug` và tên tiếng Anh (cùng tên tiếng Trung nếu người dùng muốn). Không được chứa tên kênh hay tên người.

```sh
sh bin/studio learn save <set> --slug <slug> --en "<English Name>" [--cn "<中文名>"] --based-on <based_on> [--accept-proof]
```

Lệnh tự chặn: slug trùng, tên kênh, media hay bản chép lời trong gói. Lỗi thì sửa theo thông báo rồi chạy lại.

Lệnh ghi thêm `shots.json` (số đo cách quay mà `qc shots` so với). **Học lại một phong cách đã có**: bắt đầu từ bản `STYLE.md`, `EVIDENCE.md`, `style.json` hiện có của nó, giữ mọi dòng nhật ký sửa (sửa luật nào thì thêm dòng), rồi lưu với `--update`. Lệnh từ chối nếu mất một dòng nhật ký sửa, và giữ phim mẫu đã có.

## 10. Giữ hay xoá video tham chiếu

Hỏi đúng một câu: *"Giữ video tham chiếu của bộ <set> trên máy không? Mặc định là xoá; số liệu đo vẫn được giữ."*

```sh
sh bin/studio learn clean <set>          # mặc định, hoặc khi người dùng không trả lời rõ
sh bin/studio learn clean <set> --keep   # chỉ khi người dùng nói giữ
```

Đóng việc: `sh bin/studio job done $JOB --style <slug>`. Lỗi không tự sửa được ở bất kỳ bước nào: `sh bin/studio job fail $JOB "<lỗi ngắn>"` rồi báo người dùng.

## 11. Phim mẫu (specs/021)

Sau khi lưu, làm một phim mẫu 15–30 s theo phong cách vừa học, như phong cách của thư viện (`lib/lemo-opuscar/MY-STYLES.md` §5). Phim mẫu nên làm trong một phiên mới:
- đi đủ luồng làm phim của skill `film-make` (`.claude/skills/film-make/SKILL.md`) (kịch bản được chấm, giọng của kênh nếu có, các tầng kiểm của specs/020), câu chuyện riêng, không làm gói đăng;
- bảng cảnh lập theo `shots.json` của phong cách; `qc shots` phải không có `blurred` và không có cảnh báo cách quay nào ngoài khoảng;
- lưu vào `my-styles/<slug>/`: `DEMO.md` (theo `lib/lemo-opuscar/styles/_template/DEMO.md`), `demo/` (mã nguồn, `CREDITS`, `build.sh` có `LIB=` ở đầu, ghi ra `${OUT:-…}` ngoài `demo/`), `test.jpg`, `test.mp4` (không vào git), `demo-checks.json`;
- mục 10 (Engine) của `STYLE.md` chỉ tới `demo/` trước phong cách gốc.

Cuối cùng báo cho người dùng:
- phong cách nằm ở `my-styles/<slug>/` và đã có trong danh mục `my-styles/README.md`; xem trên giao diện ở mục **Phong cách**;
- cách dùng: *"Làm phim 30 giây theo phong cách <tên> về …"*;
- nhắc commit `my-styles/<slug>/` nếu họ muốn lưu lên git.
