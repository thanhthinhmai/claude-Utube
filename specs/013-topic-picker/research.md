# Research: Chọn đề bằng số liệu YouTube (013)

## R1. Lấy số liệu cho một đề

**Decision**: Với mỗi đề, theo `regionCode` và `relevanceLanguage` lấy từ ngôn ngữ của kênh (en → US, vi → VN, zh → TW, khác → không đặt vùng), gọi theo thứ tự:

| # | Gọi | Đơn vị | Dùng cho |
|---|---|---|---|
| 1 | `search.list q=<đề> type=video order=viewCount publishedAfter=now-365d maxResults=50` | 100 | Nhu cầu |
| 2 | `search.list q=<đề> type=video order=date publishedAfter=now-90d maxResults=50` | 100 | Độ nóng, Cạnh tranh |
| 3 | `videos.list part=statistics,snippet id=<≤100 id của 1+2>` (2 lần, mỗi lần 50 id) | 2 | lượt xem, ngày đăng |
| 4 | `channels.list part=statistics,contentDetails id=<≤100 kênh>` (≤ 2 lần) | 2 | số người đăng ký, danh sách video đã đăng |
| 5 | `playlistItems.list` của 5 kênh có video nhiều lượt xem nhất ở #1 (mỗi kênh 50 video), rồi `videos.list` cho các video đó | 5 + 5 | trung vị lượt xem của kênh (video vượt 3 lần) |
| 6 | `playlistItems.list` của mỗi kênh mẫu (tối đa 10 kênh, mỗi kênh 50 video gần nhất), tra một lần cho cả lô đề | ≤ 10 / lô | luật "kênh mẫu vừa làm" |

Tổng khoảng 214 đơn vị mỗi đề, cộng tối đa 10 mỗi lô, dưới mức 400 (FR-012).

Trước mỗi lượt gọi, máy kiểm phần hạn mức còn lại. Không đủ thì dừng: đề đó ghi "chưa chấm: hết hạn mức".

Số liệu thô (các danh sách video và kênh đã rút gọn: id, tiêu đề, kênh, ngày đăng, lượt xem, số người đăng ký) được lưu trong `raw` của đề, để chấm lại không tốn thêm (FR-004, FR-005).

**Video "cùng đề"**: mọi kết quả YouTube trả về cho từ khoá của đề, tức tin vào mức độ liên quan của YouTube, cộng thêm một bộ lọc: tiêu đề video phải chứa ít nhất một nửa số từ có nghĩa của đề (bỏ từ ngắn và từ chung chung). Bộ lọc này bỏ các kết quả lạc đề.

**Alternatives considered**: Google Trends. Bị loại vì không có API chính thức và không ổn định.

## R2. Bảng điểm (mỗi mục là số nguyên 0–10)

Gọi tập video cùng đề của lượt tìm #1 là `Y` (365 ngày), và của lượt tìm #2 là `N` (90 ngày).

**Nhu cầu**: `m` = trung vị lượt xem của 10 video nhiều lượt xem nhất trong `Y`.

| m | < 1k | ≥ 1k | ≥ 10k | ≥ 50k | ≥ 100k | ≥ 300k | ≥ 1M | ≥ 3M | ≥ 10M |
|---|---|---|---|---|---|---|---|---|---|
| điểm | 0 | 2 | 3 | 4 | 5 | 6 | 8 | 9 | 10 |

Cộng 2 điểm (tối đa 10) nếu có ít nhất một video trong `Y` vượt 3 lần trung vị lượt xem của chính kênh đăng nó (R1 #5). `Y` rỗng thì 0 điểm.

**Độ nóng**:
- `n30` = số video của `N` đăng trong 30 ngày gần nhất; `n60` = số video đăng 31–90 ngày trước.
- `r = (n30/30) / max(n60/60, 1/60)`.

| r | n30 = 0 | < 0,4 | ≥ 0,4 | ≥ 0,7 | ≥ 1,0 | ≥ 1,5 | ≥ 2,0 |
|---|---|---|---|---|---|---|---|
| điểm | 0 | 1 | 2 | 4 | 6 | 8 | 10 |

Nếu trung vị lượt xem của các video 30 ngày < 1000 thì điểm tối đa là 5 (có đăng nhưng không ai xem).

**Cạnh tranh**: `W` = tổng trọng số của các kênh khác nhau trong `N`. Trọng số theo số người đăng ký: < 10k → 0,5; < 100k → 1; < 1M → 2; ≥ 1M → 3; ẩn số người đăng ký → 1.

| W | ≤ 2 | ≤ 5 | ≤ 10 | ≤ 20 | ≤ 35 | > 35 |
|---|---|---|---|---|---|---|
| điểm | 10 | 8 | 6 | 4 | 2 | 1 |

**Trùng**: `s` = độ giống lớn nhất giữa đề và các mục kênh đã làm, gồm:
- các đề có trạng thái `made` hay `in_progress`;
- `Title` trong SCRIPT.md của các phim có bản chụp của kênh;
- ý tưởng (`input.idea`) của các việc online thuộc kênh.

Độ giống là hệ số Jaccard trên tập từ có nghĩa (chữ thường, bỏ dấu câu; tiếng không tách từ thì dùng cặp ký tự). Điểm = `round(10 × (1 − s/0,6))`, cắt trong khoảng 0–10, nên `s` ≥ 0,6 cho 0 điểm. Kênh chưa có phim thì 10 điểm.

**Hợp kênh**: điểm 0–10 do Claude chấm (R3), hoặc điểm người dùng sửa tay.

**Kết luận** (FR-003):
- GO / HOLD / DROP theo ngưỡng của spec.
- PRIORITY: đề GO có điểm độ nóng ≥ 8, và trong `n30` có ≥ 65% video đăng ở 16–30 ngày trước, tức nhịp đăng đang giảm dần về hiện tại.

**Rationale**: Ngưỡng dùng thang log cho lượt xem, vì lượt xem trên YouTube trải rộng theo cấp số. Có bảng rõ ràng thì tính tay được, nên test được (SC-001).

## Sửa sau bài chạy thật (2026-11-11)

Bài chạy với khoá thật trên 3 đề phổ biến cho thấy cách lấy số liệu của R1 #2 sai. `search order=date` chỉ trả 50 video mới nhất, nên với đề phổ biến, cả 50 video đều nằm trong 30 ngày gần nhất và phần lớn có dưới 100 lượt xem. Hệ quả: `n60 = 0`, `r` lên tới khoảng 90; độ nóng luôn bị trần 5; cạnh tranh luôn có khoảng 45 kênh, toàn kênh rất nhỏ.

Quyết định mới, thay cho R1 #2 và hai mục Độ nóng, Cạnh tranh của R2:
- Thay lượt tìm #2 bằng **hai lượt tìm theo lượt xem**: `order=viewCount publishedAfter=now-30d`, và `order=viewCount publishedAfter=now-90d publishedBefore=now-30d`. Tổng khoảng 316 đơn vị mỗi đề, vẫn dưới 400.
- Chỉ đếm **video có ít nhất 1000 lượt xem** (gọi là "video đáng kể") cho cả độ nóng và cạnh tranh. Video gần như không ai xem không phải là nhu cầu, cũng không phải đối thủ.
- **Độ nóng**: `n30` và `n60` là số video đáng kể của từng khoảng; `r` và bảng điểm giữ như cũ; bỏ trần "trung vị lượt xem < 1000".
- **PRIORITY**: tỉ lệ 65% tính trên các video đáng kể của 30 ngày.
- **Cạnh tranh**: các kênh có video đáng kể trong 90 ngày (cả hai khoảng); trọng số và bảng điểm giữ như cũ.

## R3. "Hợp kênh" và gợi ý đề bằng Claude

**Decision**: `topics_fit.run(channel, topics, suggest=False)` gọi một lượt `claude -p`, dùng cách tìm Claude và model của `editor.py` (cài đặt `editor_model`). Lượt gọi này dùng `--tools ""` (không công cụ), `--json-schema` và lời nhắc hệ thống cố định của xưởng. Đầu vào là hồ sơ kênh (CHANNEL.md, không có bài học) và danh sách đề. Đầu ra:

`{"fit": [{"topic": str, "score": 0-10, "type": "explainer|comparison|list|true story|q&a|other", "reason": "≤ 160 ký tự"}], "suggested": ["≤ 10 đề"]}`

Có `suggest` thì các đề gợi ý được chấm số liệu tiếp, rồi một lượt `claude -p` thứ hai chấm "hợp kênh" cho chúng. Tổng tối đa 2 lượt Claude mỗi lô.

Câu trả lời sai lược đồ thì gọi lại một lần. Vẫn sai thì "hợp kênh" = `null`, kết luận tạm là HOLD với lý do "fit not scored", và người dùng sửa tay được. Kiểu đề lấy từ câu trả lời của Claude; không có thì đoán theo từ khoá (`vs`, "so với" → comparison; số + "điều", "top" → list; "why", "vì sao", "how" → explainer; "?" → q&a).

## R4. Hàng đợi và các luật lấy đề

**Decision**:
- **Hàng đợi** = các đề có trạng thái `queued`, sắp theo kết luận (PRIORITY, GO, HOLD) rồi theo tổng giảm dần. Đề DROP có trạng thái `dropped`.
- **`take`** lấy đề đầu tiên thoả cả 3 điều:
  - không bị đánh dấu `blocked_reference`;
  - kiểu đề khác kiểu chung của cả 2 phim gần nhất của kênh (2 đề `made` hoặc `in_progress` gần nhất theo thời điểm lấy);
  - không cũ quá 14 ngày, hoặc người dùng chấp nhận đề cũ.
- Mỗi đề bị bỏ qua được ghi kèm lý do. Đề được lấy chuyển sang `in_progress`, gắn mã phim.
- Phim xong thì đề chuyển sang `made`:
  - local: lệnh `topics made <kênh> <số>`, hoặc tự động khi `publish` của phim đó đạt;
  - online: worker chuyển khi việc phim gắn đề xong.
- **Trùng đề**: độ giống ≥ 0,8 với một đề đã có thì chấm lại đề cũ, không thêm đề mới.
- **"Kênh mẫu vừa làm"**: một video của kênh mẫu đăng trong 30 ngày qua có tiêu đề với độ giống ≥ 0,5 so với đề.

## R5. Khoá, hạn mức, số liệu tạm

**Decision**:
- **Local**:
  - `studio config youtube-key` đọc khoá bằng `getpass` (nhập kín, không qua dòng lệnh hay chat), gọi thử `videos.list` một video công khai để kiểm, rồi ghi vào `~/.config/claude-utube/youtube.key` (quyền 600). Biến môi trường `YOUTUBE_API_KEY` thắng tệp này (dùng cho máy chủ không có tệp).
  - Hạn mức được đếm trong `.studio/youtube-usage.json` của dự án (bị git bỏ qua), theo ngày giờ Thái Bình Dương, giống hạn mức của YouTube.
- **Online**:
  - proxy nhận `POST /internal/youtube {endpoint, params}` kèm mã của việc;
  - chỉ cho phép 4 endpoint: `search`, `videos`, `channels`, `playlistItems`;
  - kiểm và cộng hạn mức (giá theo endpoint) dưới khoá tiến trình, rồi gọi `https://www.googleapis.com/youtube/v3/<endpoint>` (đổi được bằng `STUDIO_YOUTUBE_URL` cho test) với khoá đọc từ `$STUDIO_DATA/secrets/youtube.key`;
  - trả JSON nguyên văn; lỗi trả về bị bỏ phần có khoá.
- **Số liệu tạm**: khoá theo endpoint cùng tham số, giữ 24 giờ (FR-013). Lượt lấy từ số liệu tạm không cộng hạn mức.
- **Giấu khoá**: không bao giờ in khoá. Thông báo lỗi chỉ ghi 4 ký tự cuối. Mọi chuỗi ra ngoài (lỗi, log) đi qua `redact(text, key)`.

## R6. Loại việc `topics` (online)

**Decision**:
- `POST /api/v1/channels/{slug}/topics/score {topics: [...], suggest: bool}` kiểm:
  - khoá đã đặt (`503 youtube_not_ready` khi chưa);
  - hạn mức đề trong ngày của người đó: số đề trong các việc `topics` hôm nay + số đề lần này ≤ `topics_per_day`, nếu không thì `429 topics_limit` kèm giờ được chấm lại.
- Rồi tạo việc `kind: "topics"` (`charged: false`, không trừ lượt phim) với `input {channel, topics, suggest}`, gắn bản chụp hồ sơ kênh, danh sách kênh mẫu và các mục kênh đã làm (cho mục "trùng").
- `agent.py` thấy `kind == "topics"` thì gọi `topics.run_job(work)`: chấm số liệu qua proxy, gọi `claude -p` qua proxy với mã của việc, rồi ghi `work/topics-result.json`.
- Worker, khi việc `topics` kết thúc, đọc tệp kết quả và gộp vào `channels/<slug>/topics.json` của chủ việc, rồi đánh dấu việc xong. Việc này không qua cổng QC, không cần `job done`.

## R7. Nơi lưu và git

**Decision**:
- `channels/<slug>/topics.json`, `channels/<slug>/TOPICS.md` và `channels/<slug>/references.json` được thêm vào `.gitignore`.
- `TOPICS.md` liệt kê: hàng đợi (kết luận, tổng, 5 điểm, kiểu, video bằng chứng, ngày tuổi); các đề bị chặn kèm lý do; các đề DROP.
- Tên kênh đối thủ chỉ nằm trong các tệp này.
