# Hiến pháp dự án claude-Utube

claude-Utube là một **xưởng phim cho Claude**. Xưởng có hai việc: học phong cách hình ảnh và âm thanh từ các kênh YouTube, và làm phim bằng code theo phong cách đó hoặc theo các phong cách có sẵn trong thư viện.

Các lệnh `/speckit-plan`, `/speckit-analyze` và `/speckit-converge` đều kiểm tra theo file này. Vi phạm một nguyên tắc **PHẢI** được coi là lỗi nghiêm trọng nhất.

## Nguyên tắc cốt lõi

### I. Spec là nguồn sự thật
- Mọi tính năng **PHẢI** bắt đầu từ `spec.md` (cái gì và vì sao). Không viết code khi chưa có spec đã duyệt.
- Spec **KHÔNG ĐƯỢC** nhắc công nghệ. Công nghệ chỉ nằm trong `plan.md`.
- Khi yêu cầu thay đổi: sửa spec trước, rồi mới sửa plan, tasks và code.
- Ngoại lệ duy nhất là thay đổi ở **mức Trực tiếp** theo định nghĩa trong `CLAUDE.md`. Những thay đổi này vẫn **PHẢI** được kiểm chứng (nguyên tắc IV).

### II. Không đoán
- Mọi chỗ mơ hồ **PHẢI** được đánh dấu `[NEEDS CLARIFICATION: câu hỏi]` và hỏi người dùng.
- Không tự thêm tính năng "có thể cần sau này" (YAGNI).

### III. MVP trước, chia theo user story
- User story được xếp ưu tiên P1, P2, P3. P1 **PHẢI** tự chạy được và tự test được.
- Làm xong và kiểm chứng xong một story rồi mới chuyển sang story tiếp theo.

### IV. Đo được, kiểm chứng được
- Mỗi tiêu chí thành công **PHẢI** đo được bằng số liệu. Không dùng các từ như "đẹp" hay "giống".
- Logic quan trọng **PHẢI** có test tự động. Với hình, âm thanh và phim, **PHẢI** có thêm kiểm tra bằng số liệu (khung hình, màu, độ lớn âm thanh, thời gian) và xem thử thật.
- Không được báo "xong" khi chưa chạy kiểm chứng. Kết quả kiểm chứng ghi rõ: đạt, đạt một phần, hoặc thất bại. Bước nào không chạy được trong môi trường hiện tại thì **PHẢI** nói rõ.

### V. Đơn giản
- Bắt đầu với cấu trúc tối thiểu, dùng công cụ trực tiếp, không bọc thêm lớp trừu tượng khi chưa cần.
- Mọi độ phức tạp vượt mức **PHẢI** được giải thích trong mục "Complexity Tracking" của `plan.md`.

### VI. Thư viện gốc được giữ nguyên
- Thư viện phong cách bên ngoài (lemo-opuscar) **PHẢI** được giữ nguyên để cập nhật được từ bản gốc. Không sửa file bên trong nó.
- Mọi phần mở rộng (phong cách riêng, công cụ, skill) nằm **bên ngoài** thư viện, trong thư mục của dự án.

### VII. Một bộ máy dựng hình
- Toàn dự án dùng **một** bộ máy dựng hình chính. Bộ máy nào được chốt trong `plan.md` của tính năng đầu tiên cần dựng hình, kèm so sánh trong `research.md`.
- Thêm bộ máy thứ hai chỉ khi có lý do ghi trong "Complexity Tracking" và được người dùng duyệt.

### VIII. Học phong cách bằng đo, không bằng cảm nhận
- Học phong cách từ kênh YouTube theo phương pháp của claude-animated-shorts: xem đủ mọi khung hình, đo bằng công cụ, rút ra luật kèm con số. Chỉ lấy **phương pháp** và **style bible**, không lấy code dựng hình của repo đó.
- Kết luận nào cũng **PHẢI** có số đo hoặc khung hình làm bằng chứng. Kết luận nào sai khi kiểm tra lại thì **PHẢI** được sửa.
- Phong cách học được **PHẢI** lưu theo định dạng phong cách của thư viện (khung 11 mục), để dùng giống như phong cách có sẵn.

### IX. Spec-kit cho phần mềm, không cho từng phim
- Quy trình spec-kit dùng để xây xưởng: skill, công cụ, cấu trúc.
- Mỗi bộ phim đi theo quy trình làm phim của thư viện (brief → treatment → dựng → kiểm tra), **không** tạo spec cho từng phim.

## Bản quyền và nội dung

- Video tải từ kênh tham chiếu chỉ để học nội bộ: **không** đăng lại, **không** gửi đi, **không** commit vào repo.
- Ở dịch vụ online cho khách (giai đoạn 2), xưởng được tải video từ kênh YouTube khách nêu, **chỉ** để học phong cách, với các điều kiện:
  - Khách **PHẢI** xác nhận trước khi tải rằng họ có quyền dùng video, hoặc chỉ dùng để nghiên cứu phong cách.
  - Video nằm riêng trên máy chủ: **không** hiện, **không** phát, **không** cho tải về, **không** chia sẻ cho ai, kể cả chính khách.
  - Video **PHẢI** bị xoá khi học xong (đạt, dừng hoặc lỗi). Chỉ giữ số đo và vài khung hình làm bằng chứng cho bản phong cách.
  - Chủ xưởng chịu rủi ro pháp lý (điều khoản YouTube, bản quyền). Nên hỏi luật sư trước khi mở cho công chúng.
- Phim làm ra chỉ học **phong cách**. Câu chuyện, nhân vật, giọng đọc và nhạc **PHẢI** là của mình. Không nêu tên kênh tham chiếu trong phim.
- Tài sản bên thứ ba (font, hình, nhạc, mô hình, dữ liệu) chỉ dùng loại có giấy phép rõ ràng (CC0, CC BY, OFL, MIT) và **PHẢI** ghi vào `CREDITS`.
- Không commit secret, API key hay file media nặng vào repo.

## Phần mềm hệ thống

- Xưởng, khi phát triển và khi chạy bằng lệnh, **KHÔNG ĐƯỢC** tự cài phần mềm hệ thống (gói của hệ điều hành, trình điều khiển, tính năng của Windows hay macOS). Thiếu thì báo người dùng thứ còn thiếu và cách cài.
- Ngoại lệ duy nhất là **app desktop** (specs/015 trở đi): app được bật một tính năng của hệ điều hành mà nó cần (ví dụ WSL2 trên Windows) **chỉ khi** người dùng tự bấm nút yêu cầu trong app **và** đồng ý quyền quản trị trong hộp hỏi của hệ điều hành. Trước khi bấm, app **PHẢI** nói rõ sẽ bật gì và có cần khởi động lại máy không. App không bật gì khi chưa có hai bước đồng ý đó.

## Quy trình làm việc

1. Chọn mức quy trình theo `CLAUDE.md`:
   - **Trực tiếp:** sửa rồi kiểm chứng.
   - **Nhẹ:** `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`.
   - **Đầy đủ:** `/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement` → `/speckit-converge`.
2. Người dùng duyệt kết quả sau mỗi bước rồi mới chạy bước tiếp theo.
3. Mỗi tính năng nằm trên nhánh riêng `NNN-ten-tinh-nang` và thư mục riêng `specs/NNN-ten-tinh-nang/`.
4. Commit sau mỗi giai đoạn trong `tasks.md` hoàn thành.

## Quản trị

- Hiến pháp này có hiệu lực cao hơn mọi hướng dẫn khác trong dự án.
- Muốn sửa hiến pháp thì phải ghi lý do, được người dùng duyệt và tăng số phiên bản.

**Version**: 2.2.0 | **Ratified**: 2026-11-05 | **Last Amended**: 2026-11-11

### Lịch sử sửa đổi
- 2.2.0: Thêm mục "Phần mềm hệ thống": xưởng không tự cài phần mềm hệ thống; ngoại lệ cho app desktop bật tính năng của hệ điều hành (WSL2) khi người dùng bấm và đồng ý quyền quản trị.
- 2.1.0: Cho phép dịch vụ online tải video từ kênh YouTube khách nêu để học phong cách, kèm điều kiện (xác nhận quyền, giữ kín, xoá sau khi học).
- 2.0.0: Hiến pháp riêng cho claude-Utube. Thêm nguyên tắc VI–IX và mục bản quyền, nội dung.
- 1.1.0: Thêm 3 mức quy trình (Trực tiếp, Nhẹ, Đầy đủ) để tiết kiệm token.
- 1.0.0: Hiến pháp chung ban đầu.
