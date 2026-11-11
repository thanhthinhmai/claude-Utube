# Research: Hồ sơ kênh và tệp bài học (012)

## R1. Nơi lưu và khuôn dạng

**Decision**:
- Mỗi kênh có thư mục `<gốc>/channels/<mã>/`, gồm `channel.json` (máy đọc và ghi), `lessons.json`, cùng `CHANNEL.md` và `LESSONS.md` (viết lại từ JSON sau mỗi lần ghi).
- `<gốc>` = `store.root()`: thư mục dự án khi chạy local, `$STUDIO_DATA/accounts/<id>` khi chạy online.
- Bài học chung:
  - local: `channels/lessons.json` cùng `channels/LESSONS.md`;
  - online: `$STUDIO_DATA/shared/lessons.json`, chỉ admin sửa.
- Local có thêm `channels/README.md` làm danh mục, như `my-styles/README.md`.
- Ghi tệp an toàn: ghi ra tệp tạm rồi đổi tên.
- Sửa tay: người dùng sửa `channel.json` hoặc `lessons.json`. Lệnh `channel show` kiểm lại và báo lỗi nếu sai; Markdown được viết lại ở lần ghi sau.

**Rationale**: Không cần thêm bảng. Dữ liệu tự đi theo luật xoá tài khoản (007 FR-026) và theo git ở local (Q2).

**Alternatives considered**:
- Bảng SQLite cho kênh. Bị loại vì bản local không có SQLite, nên sẽ phải có hai cách lưu.
- Chỉ dùng Markdown. Bị loại vì cần bộ đọc Markdown, dễ vỡ khi người dùng sửa tay.

## R2. Bản chụp kênh trong thư mục phim

**Decision**: `channel attach <phim> <mã> [--style S] [--seconds N] [--language L] [--voice V] [--speed X]` viết vào thư mục phim:
- **`channel.json`**: mã kênh, thời điểm chụp; các giá trị dùng cho phim (sau khi áp giá trị riêng của phim); `rules` (ngôn ngữ, từ cấm, hashtag bắt buộc, độ dài tối đa của tiêu đề, giọng, tốc độ, `voice_override` khi phim chọn giọng riêng); `lessons` (các bài học `active` có luật máy hợp lệ: số, phạm vi `channel` hoặc `shared`, luật).
- **`CHANNEL_BRIEF.md`**: hồ sơ (bỏ trường rỗng), quyết định, rồi bài học `active` (có luật máy trước, sau đó mới nhất trước), mỗi bài học một dòng "#n lỗi → cách chặn". Cắt ở 6000 ký tự. Bị cắt thì lệnh in cảnh báo và brief ghi dòng cuối "(N lessons not shown: merge or retire some)".

Các máy chấm chỉ đọc bản chụp. Phim không có `channel.json` thì không thêm luật nào (SC-006). Chạy lại `attach` sẽ cập nhật bản chụp; ở local đó là lựa chọn của người dùng.

**Rationale**: Container online chỉ thấy thư mục việc (007). Kết quả chấm lặp lại được. Phim cũ không bị kiểm lại (edge case của spec).

## R3. Các luật mới và cách khớp

**Decision**:
- **Từ cấm và luật `phrase:`**: chuẩn hoá chữ thường và NFC. Ngôn ngữ có khoảng trắng thì khớp trọn từ bằng ranh giới `(?<!\w)…(?!\w)` trên chữ đã chuẩn hoá; "sốc" không khớp "sốt". Chữ CJK (theo `publish.is_cjk`) thì khớp chuỗi con.
- **`script check`** (đều là điều kiện cứng):
  - `channel_language`: `Language` của SCRIPT.md bằng `rules.language`;
  - `banned_word`: từng chỗ, báo kèm `Pnn.câu`;
  - `lesson_rule`: báo kèm `#n`, cho `phrase:` và `max_sentence_words:`. Đây là lỗi nặng (FR-011).
- **`publish`** (mã lỗi mới):
  - `channel_hashtags`: thiếu hashtag bắt buộc; so không phân biệt hoa thường;
  - `channel_banned`: từ cấm trong tiêu đề, `hook`, `summary`, tên chương, chữ trên thumbnail;
  - `channel_title_max`: tiêu đề dài hơn độ dài tối đa của kênh;
  - `lesson_rule`: cho `phrase:` và `max_title_chars:`. Gói còn lỗi `lesson_rule` sau vòng sửa thì `PUBLISH.md` có dòng đầu "⚠ Do not publish yet: repeats lesson #n", và `qa.publish.blocked_by_lesson = [n…]` (Q4).
- **`qc`**: `channel_voice`. Khi bản chụp có `rules.voice` và không có `voice_override`, mọi dòng của `lines.json` phải có `voice` bằng giọng của kênh. Dòng không ghi `voice` được tính là giọng mặc định của thư viện (`af_bella`). `speed` lệch hơn 0,01 cũng là lỗi.
- **Luật máy hợp lệ**: `phrase:<1–80 ký tự>`, `max_sentence_words:<5–60>`, `max_title_chars:<20–100>`. Luật khác thì đánh dấu `invalid` lúc ghi (FR-010), và lệnh in cảnh báo.

**Alternatives considered**: cho phép biểu thức chính quy làm luật máy. Bị loại vì người dùng khó viết đúng, và một biểu thức tệ có thể làm treo máy chấm.

## R4. Biên tập độc lập

**Decision**: `editor.run()` thêm `CHANNEL_BRIEF.md` (nếu có) vào danh sách tệp biên tập được đọc. Lời nhắc hệ thống thêm một câu: "If CHANNEL_BRIEF.md exists, the script must fit the channel's audience and voice; repeating a recorded lesson is P1." Lược đồ trả lời không đổi.

## R5. Soạn nháp và duyệt bài học

**Decision**:
- **Local**: Claude trong khung chat soạn từ lời người dùng kể, chạy `studio lesson draft <mã|shared> --film F --what … --why … --stop … [--rule …]`, in bài học nháp, rồi hỏi người dùng duyệt trong khung chat. Duyệt thì chạy `lesson approve <mã|shared> <n>`. Người dùng cũng tự sửa được `lessons.json`.
- **Online, việc sửa phim có `lesson: true`**: lời nhắc dặn agent viết `films/<mới>/LESSON_DRAFT.json` (`what`, `why`, `stop`, `rule?`) từ ghi chú. Khi việc xong, worker gọi `channels.add_lesson(..., status="draft")` vào kênh của phim. Trang kênh hiện nháp với nút "Approve" và "Edit".
- **Online, tự viết**: form trên trang kênh tạo thẳng bài học `active`, vì chính người dùng viết.
- Số bài học: lớn nhất + 1 trong tệp đó, kể cả `retired` và `draft`; không bao giờ dùng lại.

## R6. Online

**Decision**:
- **API** (contracts/api.md): `GET/POST /channels`, `GET/PUT /channels/{slug}`, `POST /channels/{slug}/decisions`, `GET/POST /channels/{slug}/lessons`, `POST /channels/{slug}/lessons/{n}/approve|retire`, `PUT /channels/{slug}/lessons/{n}` (chỉ khi còn `draft`), `GET/POST /lessons/shared` và `POST /lessons/shared/{n}/retire` (admin; người khác nhận 403).
- Quyền theo `store.as_account`, như phim và phong cách. Người khác nhận 404 (SC-005).
- **`POST /jobs`** thêm `channel`. Khi có kênh, `style`, `seconds` và ngôn ngữ lấy từ hồ sơ nếu body không gửi; kênh không có thì 404; phong cách của kênh không còn thì 422 (edge case).
- Worker `prepare()` gọi `channels.attach(...)` với gốc của chủ việc và bài học chung của xưởng, viết bản chụp vào `work/films/<phim>/`. Việc sửa phim dùng lại kênh của phim cũ.
- **Giao diện**: route `#/channels`, `#/channels/<slug>`, và mục admin "Shared lessons" trong Settings. Form giao phim có `<select id="f-channel">`; đổi kênh thì điền phong cách và độ dài.
- **Giới hạn**: 20 kênh mỗi người, 200 bài học mỗi kênh. Vượt thì 409 `limit`.

## R7. Giọng đọc

**Decision**: Hồ sơ lưu `voice` (chuỗi) và `speed` (0,5–2,0). Khi lưu, chỉ kiểm tên giọng theo dạng:
- Kokoro: `^[a-z]{2}_[a-z]+$`, ví dụ `af_bella`;
- edge-tts: `^[a-z]{2,3}-[A-Z]{2,4}-\w+Neural$`.

Nếu có tệp danh sách giọng của thư viện thì đối chiếu thêm với danh sách đó. Spec nói "giọng có sẵn của thư viện"; kiểm theo dạng tên đã chặn được tên lạ và đường dẫn tệp, tức chặn được việc dùng giọng clone. Giới hạn: không kiểm được rằng giọng thật sự có trong mô hình khi máy không cài gói giọng.

**Alternatives considered**: gọi `tts.py` để thử giọng khi lưu. Bị loại vì chậm và cần mô hình giọng.
