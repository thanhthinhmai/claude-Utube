# Feature Specification: Ghi chú từng shot trên trang phim

**Feature Branch**: `029-shot-notes`

**Created**: 2026-11-23

**Status**: Draft

**Input**: User description: "Ghi chú từng shot trên trang Film detail để sửa lại phim (029-shot-notes). Trang Film detail của app có thêm phần "Shots": thanh thời gian chia ô theo từng shot (rộng theo độ dài, màu theo trạng thái), danh sách shot (số shot, 3 ảnh nhỏ đầu/giữa/cuối, khoảng thời gian, ghi chú còn mở, nhãn trạng thái), bộ lọc All / Needs fix / Fixed / No notes, khung shot đang chọn (ảnh to, phát riêng shot đó, Prev/Next, trạng thái No issue / Needs fix / Fixed, danh sách ghi chú có mốc giây tuỳ chọn và ô tick đã sửa, ô thêm ghi chú), và ô "Fix with Claude" có câu lệnh để copy dán vào chat. Mốc shot đọc từ tệp shots.json cạnh video (dạng [[t0, t1, bối cảnh, mã cảnh]] như window.SHOTS của phim dựng bằng trang web); phim dựng bằng After Effects ghi shots.json khi ghép bản tổng; phim không có shots.json thì phần Shots báo chưa có mốc shot. Ghi chú và trạng thái lưu trong tệp shot-notes.json của thư mục phim, ghi qua API của app (chỉ đọc/ghi trong thư mục phim). Vòng sửa: người dùng nhắn Claude "Sửa theo ghi chú phim <tên>", Claude đọc shot-notes.json, sửa code shot, dựng lại bằng AE, thay video và tick ghi chú. Không nối app với AE ở bản này; bản đầu không có ảnh đính kèm. Mockup: https://claude.ai/artifact/LmF4iZkvMAUas6WoCxw8zb"

## Clarifications

### Session 2026-11-23

- Q: Bản đầu có cho đính kèm ảnh vào ghi chú không? → A: Có. Ghi chú nhận ảnh bằng dán Ctrl+V (ảnh chụp màn hình trong clipboard) hoặc chọn tệp; tối đa 4 ảnh mỗi ghi chú.
- Q: Phần Shots làm cho mọi phim hay chỉ phim After Effects? → A: Mọi phim. Phim dựng bằng trang web tự có tệp mốc shot sau khi dựng hình; có thêm một lệnh tạo tệp mốc shot cho phim cũ từ trang phim, không dựng lại hình.
- Q: Khi sửa xong, có giữ video cũ để so trước/sau không? → A: Giữ đúng 1 bản trước (cùng mốc shot của nó); trang phim có nút "Xem bản trước" cho shot đang chọn.
- Q: Ghi chú shot chỉ ở trang phim đã xong hay cả trang việc lúc đang làm? → A: Chỉ trang phim đã xong; trang việc có đường dẫn "Ghi chú shot" sang trang phim khi phim đã có video.

## Bối cảnh

- Người dùng đang luyện làm phim bằng After Effects theo từng đợt 10 shot. Mỗi đợt họ xem bản so sánh, chụp màn hình, khoanh chỗ sai rồi nhắn vào chat ("shot 31 thiếu tay", "shot 39 logo sai"). Ghi chú nằm rải trong chat, hay nhầm số shot (ví dụ gọi shot 37 là "shot 39"), và không có chỗ xem lỗi nào đã sửa.
- Trang phim của app hiện chỉ có video, bảng kết quả kiểm tra, kịch bản và giấy phép. Không có cách xem hay ghi chú theo từng shot.
- Phim dựng bằng trang web của xưởng đã biết mốc từng cảnh (`SHOTS` của trang phim). Phim dựng bằng After Effects biết thứ tự và độ dài shot khi ghép bản tổng, nhưng chưa ghi ra ngoài.
- Mockup đã duyệt hướng: https://claude.ai/artifact/LmF4iZkvMAUas6WoCxw8zb

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Xem phim theo từng shot (Priority: P1)

Người dùng mở trang một phim đã xong. Dưới video có thanh thời gian chia ô theo từng shot và danh sách shot: số shot, ba ảnh nhỏ (đầu, giữa, cuối shot), khoảng thời gian và độ dài. Bấm một shot thì shot đó được chọn: thấy ảnh to, phát được riêng shot đó (phát tới hết shot thì dừng), và chuyển sang shot trước hoặc sau.

**Why this priority**: Không có mốc shot thì không ghi chú theo shot được. Chỉ riêng phần này đã giúp người dùng tìm và nói đúng số shot khi báo lỗi.

**Independent Test**: Đặt tệp mốc shot cho phim `ae-crayon-test` (40 shot), mở trang phim: thấy 40 ô trên thanh thời gian, 40 dòng shot có ảnh. Bấm shot 37 thì video phát từ 1:55.3 và dừng ở 2:02.1.

**Acceptance Scenarios**:

1. **Given** phim web đã xong trong kho của app (ví dụ `pet-swap`) chưa có tệp mốc shot, **When** chạy lệnh tạo tệp mốc shot cho phim đó, **Then** tệp được tạo từ trang phim mà không dựng lại hình, và mở trang phim thấy phần Shots.
2. **Given** phim có video và tệp mốc shot, **When** mở trang phim, **Then** thanh thời gian có đúng một ô cho mỗi shot, độ rộng ô tỉ lệ với độ dài shot, và danh sách có một dòng cho mỗi shot theo thứ tự thời gian.
3. **Given** danh sách shot, **When** nhìn một dòng, **Then** thấy số shot, ba ảnh lấy ở khoảng 12%, 50% và 88% thời lượng shot, khoảng thời gian (phút:giây) và độ dài (giây).
4. **Given** một shot được chọn, **When** bấm "Phát shot này", **Then** video phát từ đầu shot và dừng trong vòng 0,2 giây quanh cuối shot.
5. **Given** shot đang chọn, **When** bấm Prev hoặc Next, **Then** shot liền trước hoặc liền sau được chọn; ở shot đầu không lùi được, ở shot cuối không tiến được.
6. **Given** phim có video nhưng không có tệp mốc shot, **When** mở trang phim, **Then** phần Shots hiện một dòng báo "Phim này chưa có mốc shot" kèm cách tạo, và phần còn lại của trang vẫn như cũ.

---

### User Story 2 - Ghi chú lỗi và trạng thái từng shot (Priority: P1)

Ở shot đang chọn, người dùng viết ghi chú lỗi, có thể ghim vào một giây trong shot (ví dụ 0:05 tính từ đầu shot), và đặt trạng thái shot: Không lỗi, Cần sửa, Đã sửa. Mỗi ghi chú có ô tick "đã sửa". Ghi chú và trạng thái được lưu cùng phim, mở lại trang hay mở từ máy khác vẫn thấy. Thanh thời gian tô màu ô theo trạng thái; bộ lọc cho xem nhanh các shot Cần sửa, Đã sửa, chưa có ghi chú.

**Why this priority**: Đây là mục đích chính của tính năng: gom lỗi vào một chỗ, gắn đúng shot, theo dõi được cái nào đã sửa.

**Independent Test**: Chọn shot 37, thêm ghi chú "tay người ngồi bị bàn che" ghim ở 0:05, tải lại trang: ghi chú còn, shot 37 có nhãn "Cần sửa", ô 37 trên thanh thời gian màu "Cần sửa", bộ lọc "Cần sửa" có shot 37.

**Acceptance Scenarios**:

1. **Given** shot đang chọn, **When** nhập chữ và bấm "Thêm ghi chú", **Then** ghi chú hiện ngay trong danh sách của shot, được lưu, và shot chuyển sang "Cần sửa" nếu đang là "Không lỗi" hoặc chưa có trạng thái.
2. **Given** ô "Ghim vào giây hiện tại" được bật, **When** thêm ghi chú lúc video đang ở trong shot, **Then** ghi chú mang mốc giây tính từ đầu shot (một chữ số thập phân); tắt ô đó thì ghi chú áp cho cả shot.
3. **Given** một ghi chú có mốc giây, **When** bấm mốc đó, **Then** video nhảy tới đúng thời điểm ấy trong phim.
4. **Given** một ghi chú còn mở, **When** tick "đã sửa", **Then** ghi chú hiện là đã sửa (gạch ngang, mờ đi). Khi mọi ghi chú của shot đã sửa, shot tự chuyển sang "Đã sửa"; bỏ tick một ghi chú thì shot quay lại "Cần sửa".
5. **Given** shot đang chọn, **When** bấm một trong ba nút trạng thái, **Then** shot lấy trạng thái đó, kể cả khác với trạng thái tự suy từ ghi chú. Lần đổi ghi chú sau thì trạng thái lại tự suy theo luật ở kịch bản 4.
6. **Given** phim có ghi chú, **When** chọn bộ lọc "Cần sửa" (hoặc "Đã sửa", "Chưa có ghi chú", "Tất cả"), **Then** danh sách chỉ còn các shot đúng trạng thái, kèm số lượng trên nút lọc; thanh thời gian vẫn hiện đủ mọi shot.
7. **Given** hai người cùng mở trang và cùng sửa ghi chú của một phim, **When** người thứ hai lưu sau khi người thứ nhất đã lưu, **Then** không ghi chú nào bị mất: thay đổi của hai người cùng còn, hoặc người thứ hai được báo nội dung đã đổi và được tải lại trước khi lưu.
8. **Given** một ghi chú, **When** sửa chữ hoặc xoá ghi chú, **Then** thay đổi được lưu; xoá phải bấm xác nhận.
9. **Given** ô nhập ghi chú đang được chọn và trong clipboard có ảnh (ví dụ ảnh chụp màn hình có khoanh đỏ), **When** bấm Ctrl+V, **Then** ảnh hiện thành ảnh nhỏ trong ghi chú đang viết; bấm "Thêm ghi chú" thì ảnh được lưu cùng ghi chú. Chọn tệp ảnh từ máy cũng làm được như vậy.
10. **Given** ghi chú có ảnh, **When** bấm ảnh nhỏ, **Then** ảnh mở to; xoá ảnh khỏi ghi chú thì ảnh không còn hiện ở đâu nữa.

---

### User Story 3 - Gửi ghi chú cho Claude sửa và nhận phim mới (Priority: P2)

Ở trang phim có ô "Sửa cùng Claude" với câu lệnh sẵn ("Sửa theo ghi chú phim <tên>") và nút Copy. Người dùng dán câu đó vào chat. Claude đọc ghi chú còn mở của phim, sửa đúng các shot đó, dựng lại, thay video của phim, tick các ghi chú đã sửa và ghi một dòng trả lời vào ghi chú. Phim dựng bằng After Effects ghi tệp mốc shot mỗi lần ghép bản tổng, nên thanh thời gian luôn khớp video mới.

**Why this priority**: Khép vòng sửa, nhưng phần ghi chú (P1) đã có ích riêng: người dùng vẫn có thể tự đọc ghi chú và nhắn chat như hiện nay.

**Independent Test**: Phim `ae-crayon-test` có một ghi chú mở ở shot 37. Nhắn Claude câu lệnh đã copy. Sau khi Claude báo xong: video của phim trên app là bản mới (thời điểm sửa tệp mới hơn ghi chú), ghi chú shot 37 đã tick, có dòng trả lời của Claude, tệp mốc shot có 40 shot khớp độ dài video trong 0,1 giây.

**Acceptance Scenarios**:

1. **Given** trang phim, **When** bấm Copy ở ô "Sửa cùng Claude", **Then** câu lệnh có tên phim được chép vào bộ nhớ tạm và nút báo "Đã chép" trong khoảng 1,5 giây.
2. **Given** phim có ghi chú mở, **When** người dùng nhắn Claude câu lệnh, **Then** Claude liệt kê lại các ghi chú mở (shot, mốc giây, nội dung) trước khi sửa, để người dùng thấy Claude đọc đúng.
3. **Given** Claude đã sửa và dựng lại xong, **When** mở lại trang phim, **Then** video là bản mới, các ghi chú Claude đã sửa được tick, mỗi ghi chú đó có dòng trả lời ngắn của Claude (đã đổi gì), và ghi chú Claude không sửa được vẫn mở kèm lý do.
4. **Given** phim dựng bằng After Effects, **When** ghép bản tổng, **Then** tệp mốc shot được ghi cạnh video, số shot và tổng độ dài khớp bản tổng (sai lệch ≤ 1 khung hình).
5. **Given** Claude vừa thay video của phim, **When** chọn một shot và bấm "Xem bản trước", **Then** đoạn của shot đó trong bản video trước được phát (theo mốc shot của bản trước), để so với bản mới; lần thay video kế tiếp thì bản trước cũ bị bỏ, chỉ giữ một bản.
6. **Given** phim bị dựng lại làm đổi độ dài một shot, **When** mở trang phim, **Then** ghi chú vẫn gắn đúng số shot; mốc giây trong shot vẫn tính từ đầu shot đó.

---

### Edge Cases

- Tệp mốc shot hỏng, khoảng thời gian chồng nhau, có lỗ hở, hoặc vượt độ dài video: phần Shots báo tệp mốc shot không hợp lệ (nói rõ dòng nào), không vẽ thanh thời gian sai, và không chặn phần còn lại của trang.
- Số shot trong tệp ghi chú không còn trong tệp mốc shot (phim dựng lại bỏ bớt shot): ghi chú đó vẫn hiện trong mục "Ghi chú của shot không còn", không bị xoá âm thầm.
- Phim rất dài hoặc nhiều shot (tới 300 shot): trang vẫn mở được, ô quá hẹp trên thanh thời gian vẫn bấm được qua danh sách.
- Phim đang dựng hoặc chưa có video: phần Shots không hiện (trang như hiện nay).
- Ghi chú không chữ và không ảnh: không thêm được. Ghi chú dài quá 2.000 ký tự: bị chặn kèm thông báo.
- Dán thứ không phải ảnh (chữ) vào ô ghi chú: chữ vào ô như bình thường. Dán ảnh quá 10 MB, sai định dạng, hoặc quá 4 ảnh: bị từ chối kèm thông báo, chữ đang gõ không mất.
- Tên phim hoặc đường dẫn lạ: chỉ đọc và ghi đúng hai tệp ghi chú và mốc shot trong thư mục của phim đó, không với ra ngoài.
- Ảnh nhỏ của shot chưa có: hiện ô giữ chỗ cùng cỡ, và ảnh được tạo lại khi video đổi.
- Mã API chỉ đọc (chế độ nhiều người dùng): đọc được ghi chú nhưng không sửa được; người dùng khác không thấy phim nên không thấy ghi chú.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Trang phim PHẢI hiện phần Shots khi phim có video và tệp mốc shot hợp lệ, gồm thanh thời gian, bộ lọc, danh sách shot và khung shot đang chọn.
- **FR-002**: Tệp mốc shot PHẢI là danh sách các khoảng `[bắt đầu, kết thúc, bối cảnh, mã shot]` theo giây, nối liền từ 0 tới hết video, cùng dạng `SHOTS` mà trang phim của xưởng đã xuất. Xưởng PHẢI kiểm tệp này (nối liền, không chồng, không vượt độ dài video quá 1 khung hình) và báo dòng sai.
- **FR-003**: Phim dựng bằng trang web của xưởng PHẢI có tệp mốc shot sinh từ `SHOTS` của trang khi dựng hình xong. Phim dựng bằng After Effects PHẢI có tệp mốc shot sinh khi ghép bản tổng.
- **FR-003a**: Xưởng PHẢI có một lệnh tạo tệp mốc shot cho phim web đã xong từ `SHOTS` của trang phim, không dựng lại hình; lệnh báo lỗi rõ khi trang không xuất `SHOTS` hoặc tổng độ dài lệch video quá 1 khung hình.
- **FR-004**: Mỗi shot PHẢI có ba ảnh nhỏ ở 12%, 50% và 88% thời lượng, tạo từ video của phim; ảnh PHẢI được tạo lại khi video thay đổi.
- **FR-005**: Người dùng PHẢI phát được riêng một shot (từ đầu tới cuối shot rồi dừng) và chuyển shot trước, sau.
- **FR-006**: Người dùng PHẢI thêm, sửa, xoá ghi chú cho một shot; ghi chú có nội dung (1–2.000 ký tự), mốc giây trong shot (tuỳ chọn), tối đa 4 ảnh đính kèm, cờ "đã sửa", người viết, thời điểm tạo và sửa, và dòng trả lời (tuỳ chọn). Ghi chú chỉ có ảnh, không chữ, cũng thêm được.
- **FR-006a**: Ô nhập ghi chú PHẢI nhận ảnh dán bằng Ctrl+V (Cmd+V trên macOS) và ảnh chọn từ tệp; chỉ nhận ảnh PNG, JPEG, WebP, mỗi ảnh ≤ 10 MB. Ảnh PHẢI được lưu trong thư mục của phim cạnh sổ ghi chú, để Claude mở xem được khi sửa.
- **FR-007**: Mỗi shot PHẢI có trạng thái Không lỗi, Cần sửa, Đã sửa hoặc chưa có. Trạng thái tự suy từ ghi chú (còn ghi chú mở → Cần sửa; có ghi chú và tất cả đã sửa → Đã sửa) và người dùng PHẢI đặt tay được, đè lên trạng thái tự suy cho tới lần đổi ghi chú kế tiếp.
- **FR-008**: Ghi chú và trạng thái PHẢI được lưu trong thư mục của phim, trong một tệp đọc được bằng mắt, để Claude và công cụ của xưởng đọc thẳng được mà không cần app.
- **FR-009**: Việc ghi PHẢI không làm mất thay đổi của người khác: mỗi lần lưu kèm dấu của nội dung đã đọc; dấu không khớp thì từ chối, báo người dùng và cho tải lại.
- **FR-010**: Xưởng PHẢI chỉ đọc, ghi tệp ghi chú và tệp mốc shot nằm trong thư mục của đúng phim được yêu cầu, và từ chối tên phim, đường dẫn không hợp lệ.
- **FR-011**: Thanh thời gian PHẢI tô ô theo trạng thái bằng ba màu khác nhau cả về độ sáng (không chỉ khác sắc), có chú thích, và đánh dấu shot đang chọn.
- **FR-012**: Bộ lọc PHẢI có Tất cả, Cần sửa, Đã sửa, Chưa có ghi chú, kèm số shot mỗi loại.
- **FR-013**: Trang PHẢI có ô "Sửa cùng Claude" với câu lệnh có tên phim và nút Copy.
- **FR-014**: Quy trình làm phim (hướng dẫn cho Claude) PHẢI có bước "sửa theo ghi chú phim <tên>": đọc ghi chú mở, liệt kê lại, sửa, dựng lại, thay video, tick ghi chú đã sửa kèm dòng trả lời, để lại ghi chú chưa sửa được kèm lý do.
- **FR-014a**: Khi video của phim được thay, xưởng PHẢI giữ đúng một bản video trước cùng tệp mốc shot của bản đó; trang phim PHẢI cho phát đoạn của shot đang chọn trong bản trước. Phim chưa từng được thay thì không có nút này.
- **FR-014b**: Phần ghi chú shot chỉ nằm ở trang phim; trang việc của một phim đã có video PHẢI có đường dẫn "Ghi chú shot" mở trang phim ở phần Shots. Điểm duyệt Shots của trang việc giữ nguyên, không đọc hay ghi sổ ghi chú.
- **FR-015**: Ghi chú của shot không còn trong tệp mốc shot PHẢI vẫn hiện trong một mục riêng, không bị xoá.
- **FR-016**: Ở chế độ nhiều người dùng, mỗi người chỉ thấy và sửa ghi chú phim của chính mình; người khác không đọc được. Mã API bị giới hạn chỉ đọc thì không thêm, sửa, xoá ghi chú hay đổi trạng thái được.

### Key Entities

- **Mốc shot (của phim)**: danh sách khoảng thời gian, mỗi khoảng có số thứ tự, bắt đầu, kết thúc, bối cảnh và mã shot. Sinh ra khi dựng phim; không sửa bằng tay trên app.
- **Ghi chú shot**: thuộc một shot (theo mã shot), có nội dung, mốc giây trong shot (tuỳ chọn), tối đa 4 ảnh đính kèm, cờ đã sửa, người viết, thời điểm tạo và sửa, dòng trả lời (tuỳ chọn).
- **Ảnh đính kèm**: tệp ảnh thuộc một ghi chú, lưu trong thư mục phim; xoá ghi chú hoặc gỡ ảnh thì tệp ảnh bị xoá.
- **Trạng thái shot**: Không lỗi, Cần sửa, Đã sửa hoặc chưa có; tự suy từ ghi chú hoặc do người dùng đặt.
- **Bản video trước**: đúng một bản video cũ của phim cùng mốc shot của nó, giữ lại khi video được thay để so trước/sau.
- **Sổ ghi chú của phim**: toàn bộ ghi chú và trạng thái của một phim, kèm dấu nội dung để chống ghi đè.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Với phim 40 shot, từ lúc mở trang tới lúc ghi xong một ghi chú cho một shot mất ≤ 20 giây và ≤ 4 thao tác (chọn shot, gõ, bấm thêm), đo khi chạy thử.
- **SC-002**: Phần Shots của phim 40 shot hiện đủ thanh thời gian và danh sách (có ảnh) trong ≤ 3 giây sau khi mở trang trên máy của xưởng, kể cả lần đầu phải tạo ảnh nhỏ thì ≤ 15 giây.
- **SC-003**: Phát riêng một shot dừng trong khoảng ±0,2 giây quanh cuối shot ở 10/10 lần thử trên 10 shot khác nhau.
- **SC-004**: Hai người lưu ghi chú gần như cùng lúc trên cùng phim: 0 ghi chú bị mất qua 20 lần thử tự động.
- **SC-005**: Tệp mốc shot của phim After Effects khớp video: số shot đúng và tổng độ dài lệch ≤ 1 khung hình, ở 100% lần ghép bản tổng được test.
- **SC-006**: Trong vòng sửa thử với 3 ghi chú mở, Claude liệt kê đúng cả 3 (đúng số shot và nội dung) trước khi sửa, và sau khi xong mọi ghi chú hoặc đã tick kèm trả lời, hoặc còn mở kèm lý do (0 ghi chú bị bỏ qua không lời).
- **SC-007**: 100% yêu cầu đọc, ghi với tên phim hoặc đường dẫn không hợp lệ bị từ chối trong test tự động; không tệp nào ngoài thư mục phim bị đọc hay ghi.
- **SC-008**: Dán một ảnh chụp màn hình bằng Ctrl+V vào ghi chú rồi thêm ghi chú: ảnh hiện trong ghi chú và còn sau khi tải lại trang ở 10/10 lần thử; ảnh sai định dạng hoặc quá cỡ bị từ chối ở 100% lần thử tự động.

## Assumptions

- Ghi chú gắn theo shot, mốc giây trong shot là tuỳ chọn (theo đề xuất đã gửi người dùng). Vẽ khoanh trực tiếp trên khung hình trong app: ngoài phạm vi (người dùng khoanh bằng công cụ chụp màn hình rồi dán ảnh).
- App không gọi After Effects. Claude sửa và dựng lại khi người dùng nhắn trong chat. Nút "Gửi Claude sửa" chạy tự động từ app và nút "Mở shot trong After Effects" trên app desktop: ngoài phạm vi.
- Phần ghi chú nằm trong giao diện web của xưởng; app desktop hiện cùng giao diện đó nên có luôn, không làm riêng.
- Phim web cũ có phần Shots sau khi chạy lệnh tạo tệp mốc shot (FR-003a). Phim After Effects cũ cần ghép lại bản tổng; riêng `ae-crayon-test` được ghép lại để có tệp mốc shot làm phim mẫu.
- Ghi chú dùng ngôn ngữ người dùng gõ (thường là tiếng Việt); chữ trên giao diện theo ngôn ngữ hiện có của app.
- Ở chế độ một người (chạy trên máy), mọi người mở được app đều sửa được ghi chú.
