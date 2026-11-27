# Feature Specification: Âm thanh theo shot cho phim After Effects

**Feature Branch**: `037-sound-per-shot`

**Created**: 2026-11-25

**Status**: Draft

**Input**: User description: "037-sound-per-shot: âm thanh theo shot cho phim After Effects. Học tiếng từ video mẫu (tách lớp, phân loại bằng hai bộ phân loại độc lập, chỉ tin khi cả hai đồng ý; xét cả lớp giọng ngoài từ của người kể vì đám đông reo rơi vào đó). Map hành động → tiếng theo từng shot, tự đặt tiếng theo keyframe của shot, mốc tính lại khi thời lượng shot ở Animatic (035) đổi. Kho tiếng: gói Sonniss GDC (trên máy, ngoài git, dùng thương mại được) + Freesound chỉ CC0 lấp chỗ thiếu; ghi CREDITS; âm thanh video tham chiếu không rời máy. Điểm duyệt Sound: nghe và sửa theo từng shot."

## Bối cảnh

- Hôm nay tiếng động của phim AE được viết tay trong tệp trộn của từng phim: vài tiếng tổng hợp (vút, bụp, tách, ding), mốc tính tay theo số khung của shot. Phim thử `ae-sleepless-test` có 13 tiếng như vậy cho 9 shot; tiếng không gắn với chuyển động thật, và đổi thời lượng shot là phải sửa tay mọi mốc.
- 035 (Animatic) đặt thứ tự Script → Cast → Voice → Animatic → Sound → Final render → Publish, làm thời lượng shot thành nguồn duy nhất, và ghi rõ: âm thanh theo shot là việc của 037. Sửa ở Animatic làm Sound phải chạy lại.
- Bước học phong cách hiện đo được nhịp đọc, nhạc dưới giọng và các điểm "có tiếng động" (khởi âm mạnh ngoài lời), nhưng không biết đó là tiếng **gì**, nên không dùng được để chọn tiếng.
- Mẫu đã kiểm bằng tay (2026-11-25, `references/voice-check`, phim mẫu "500 Charisma"): kính vỡ đúng chữ "window"; gần như im hẳn ở "goes silent" (−57 dB); đám đông reo ở "people cheer" và tắt ngay ở điểm cắt; tiếng bóng; tiếng bọt nước của bể cá trong văn phòng. Tiếng đám đông reo bị bộ tách lớp xếp vào lớp **giọng**, nên chỉ xét lớp tiếng động là bỏ sót. Một bộ phân loại so trên danh sách nhãn đóng hay tự tin quá mức, nên chỉ tin khi hai bộ phân loại độc lập cùng đồng ý.
- Người dùng đã chọn (2026-11-25): kho tiếng là gói Sonniss GDC lưu trên máy (dùng thương mại được, không vào git) và Freesound **chỉ CC0** để lấp chỗ thiếu; âm thanh của video tham chiếu không bao giờ rời khỏi máy.

## Clarifications

### Session 2026-11-25

- Q: Khi kho và Freesound đều không có tiếng hợp cho một hành động, bước Sound làm gì? → A: Để trống và ghi "missing sound"; không dùng tiếng tổng hợp thay.
- Q: Học tiếng từ video mẫu chạy lúc nào? → A: Tự chạy trong học phong cách cho phong cách mới; có lệnh chạy riêng cho phong cách đã có khi video mẫu còn trên máy.
- Q: Lấp chỗ thiếu bằng Freesound diễn ra thế nào? → A: Tự động trong bước Sound khi đã có khoá; người dùng thấy và đổi được ở trang Sound.
- Q: Lấy gói Sonniss để chạy thử thật thế nào? → A: Người dùng đồng ý giấy phép Sonniss GDC (bản 2.0) và nhờ tải gói 2026 và 2024 (~31 GB) vào `E:\SoundLibrary\Sonniss` từ các mirror chính thức Sonniss ghi trên trang.
- Q: Tiếng Sonniss được dùng ở đâu, vì giấy phép cấm cung cấp tiếng gốc "như đầu ra của dịch vụ" và cấm dùng cho AI? → A: Chỉ trong phim của chủ xưởng (app trên máy, Host/Client cùng nhóm). Việc của khách ở dịch vụ online chỉ dùng Freesound CC0. Mục lục Sonniss chỉ đọc tên tệp và metadata; không chạy mô hình AI nào lên âm thanh Sonniss.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tiếng tự đặt theo chuyển động của từng shot (Priority: P1)

Sau khi Animatic được duyệt, bước Sound lập một danh sách tiếng cho từng shot từ kịch bản, lời đọc và các chuyển động của shot (ví dụ "S1: bật mắt → tiếng bụp nhỏ ở khung 17; S3: bút viết → tiếng sột soạt suốt 2 s"). Mỗi tiếng được chọn từ kho tiếng trên máy, đặt đúng mốc chuyển động, có độ lớn so với giọng theo phong cách, rồi trộn cùng giọng và nhạc thành bản Sound.

**Why this priority**: Đây là lõi của tính năng: tiếng thật, đúng chuyển động, không viết tay. Các story khác (học, duyệt) dựa vào danh sách tiếng này.

**Independent Test**: Với `ae-sleepless-test` và một kho tiếng thử nhỏ có sẵn trên máy, chạy bước Sound: mỗi shot có danh sách tiếng; mỗi tiếng gắn với một chuyển động có tên, mốc lệch ≤ 1 khung so với mốc chuyển động; bản trộn không có tiếng nào từ video tham chiếu; độ lớn giọng của bản trộn giữ trong khoảng của bước kiểm phim.

**Acceptance Scenarios**:

1. **Given** Animatic đã duyệt và kho tiếng có sẵn, **When** bước Sound chạy, **Then** mỗi shot có danh sách tiếng (tên hành động, tiếng được chọn, mốc bắt đầu theo khung của shot, độ dài, độ lớn) và bản trộn Sound được tạo.
2. **Given** một chuyển động có mốc trong shot, **When** tiếng của chuyển động đó được đặt, **Then** mốc tiếng tính từ mốc chuyển động (không phải mốc tuyệt đối gõ tay), lệch ≤ 1 khung.
3. **Given** thời lượng shot đổi ở Animatic sau khi Sound đã chạy, **When** Sound chạy lại, **Then** mọi mốc tiếng được tính lại theo thời lượng mới; tiếng của chuyển động bị cắt mất thì bị bỏ và ghi lý do; người dùng không phải sửa mốc nào bằng tay.
4. **Given** một tiếng kéo dài (tiếng nền, đám đông) chạm điểm cắt shot, **When** trộn, **Then** tiếng đó dừng ở điểm cắt theo luật của phong cách (tắt ngay hoặc tắt dần trong thời gian phong cách cho), trừ khi được đánh dấu là kéo qua cắt.
5. **Given** một khoảnh khắc lặng có chủ ý trong kịch bản (ví dụ "cả phòng im bặt"), **When** trộn, **Then** mọi lớp tiếng kể cả nhạc hạ xuống mức lặng của phong cách trong khoảng đó.
6. **Given** kho tiếng và Freesound đều không có tiếng phù hợp cho một hành động, **When** lập danh sách, **Then** hành động đó để trống, ghi "missing sound" kèm từ khoá đã tìm, không có tiếng tổng hợp thay; bước Sound vẫn chạy xong cho các tiếng còn lại.

---

### User Story 2 - Kho tiếng trên máy và lấp chỗ thiếu bằng tiếng CC0 (Priority: P1)

Người dùng tự tải các gói tiếng Sonniss GDC về một thư mục trên máy rồi chỉ cho xưởng thư mục đó. Xưởng lập mục lục cho kho (tên, loại tiếng, độ dài, nguồn, giấy phép) để tìm được theo hành động. Khi kho trên máy thiếu một tiếng, và người dùng đã nhập khoá Freesound của họ, xưởng tìm trên Freesound **chỉ các tiếng CC0**, tải về kho trên máy và ghi nguồn. Mỗi phim ghi đúng các tiếng đã dùng vào CREDITS của phim.

**Why this priority**: Không có kho thì story 1 không có tiếng để đặt. Giấy phép rõ ràng là luật của hiến pháp.

**Independent Test**: Chỉ cho xưởng một thư mục kho thử nhỏ (~12 tệp, có một tệp hỏng): mục lục có đủ một mục cho mỗi tệp đọc được, mỗi mục có nguồn và giấy phép. Với một hành động không có trong kho và khoá Freesound hợp lệ: chỉ tiếng có giấy phép CC0 được tải (100% tiếng tải về là CC0), tiếng được dùng ghi vào CREDITS của phim kèm số hiệu và đường dẫn nguồn.

**Acceptance Scenarios**:

1. **Given** người dùng chỉ một thư mục chứa gói Sonniss, **When** xưởng lập mục lục, **Then** mọi tệp tiếng đọc được có một mục (tên, loại, độ dài, nguồn "Sonniss GDC <năm>", giấy phép); tệp hỏng được liệt kê riêng, không làm dừng việc lập mục lục.
2. **Given** kho thiếu tiếng cho một hành động và có khoá Freesound, **When** bước Sound chạy, **Then** bước Sound tự tìm, chỉ tiếng có giấy phép CC0 được xét và tải; tiếng tải về vào kho trên máy với nguồn (số hiệu, người đăng, đường dẫn) và giấy phép, rồi được đặt vào phim như mọi tiếng khác.
3. **Given** không có khoá Freesound hoặc không có mạng, **When** kho thiếu tiếng, **Then** hành động ghi "missing sound" và trang Sound nói rõ có thể nhập khoá Freesound để lấp; không dừng bước Sound.
4. **Given** một phim đã có bản Sound, **When** xem CREDITS của phim, **Then** mọi tiếng đã dùng có một dòng ghi nguồn và giấy phép; CREDITS chung của xưởng ghi Sonniss GDC và Freesound (CC0) là nguồn tiếng.
5. **Given** kho tiếng, **When** kiểm repo, **Then** không tệp tiếng nào của kho nằm trong git, và bộ cài app không chứa tiếng của kho.
6. **Given** một việc của khách ở dịch vụ online, **When** bước Sound chọn tiếng, **Then** chỉ tiếng Freesound CC0 được xét; không tiếng Sonniss nào được chọn, phát thử hay gửi cho khách.
7. **Given** xưởng lập mục lục gói Sonniss, **When** kiểm cách lập, **Then** mục lục chỉ lấy từ tên tệp, thư mục và metadata trong tệp; không mô hình AI nào xử lý âm thanh Sonniss.

---

### User Story 3 - Duyệt Sound: nghe và sửa từng shot (Priority: P2)

Ở bước Sound, người dùng thấy dải thời gian (shot, câu thoại, các tiếng như khối có nhãn) và lưới shot. Bấm một shot thì phát bản nháp của shot đó với bản trộn Sound. Người dùng sửa từng tiếng: đổi sang tiếng khác (trang gợi ý vài tiếng thay thế cùng loại, nghe thử được), dời mốc, đổi độ lớn, xoá, thêm tiếng cho một hành động; hoặc ghi chú cho shot và gửi cho Claude sửa ("Send notes to Claude", như Animatic). Bản trộn được làm lại sau mỗi lần sửa; người dùng duyệt thì Final render được phép chạy.

**Why this priority**: Tiếng tự chọn sẽ có chỗ sai; người dùng phải nghe và sửa được trước bản đẹp. Nhưng story 1 và 2 đã cho ra bản Sound dùng được mà chưa cần trang sửa.

**Independent Test**: Với một phim đã có bản Sound: đổi tiếng của một hành động sang tiếng gợi ý thứ hai, dời một tiếng 5 khung, xoá một tiếng; bản trộn mới chỉ khác ở các đoạn đó (phần còn lại giống hệt từng mẫu âm thanh), các sửa được giữ khi Sound chạy lại vì thời lượng shot đổi, và nút duyệt hoạt động.

**Acceptance Scenarios**:

1. **Given** bước Sound có bản trộn, **When** người dùng bấm một shot, **Then** clip nháp của shot đó phát với bản trộn Sound của đúng đoạn đó, và danh sách tiếng của shot hiện bên cạnh.
2. **Given** một tiếng trong shot, **When** người dùng chọn "đổi tiếng", **Then** trang đưa ít nhất 3 tiếng thay thế cùng loại từ kho (nếu kho có), nghe thử được từng tiếng trước khi chọn.
3. **Given** người dùng dời, đổi độ lớn, xoá hoặc thêm một tiếng, **When** lưu, **Then** bản trộn được làm lại trong ≤ 30 s cho phim 30 s và các sửa của người dùng được ghi là "của người dùng".
4. **Given** sửa của người dùng và thời lượng shot sau đó đổi ở Animatic, **When** Sound chạy lại, **Then** sửa của người dùng được giữ, mốc được tính lại theo mốc chuyển động mà tiếng gắn vào; sửa nào không còn đặt được (chuyển động bị cắt) thì được báo, không âm thầm bỏ.
5. **Given** ghi chú trên vài shot, **When** người dùng bấm "Send notes to Claude", **Then** một việc sửa chạy nền trên app, Claude chỉ sửa tiếng của các shot có ghi chú, trả lời từng ghi chú, và bước Sound trở về chưa duyệt.
6. **Given** điểm Sound đang bật, **When** có lệnh dựng bản đẹp trước khi Sound được duyệt, **Then** lệnh bị từ chối kèm lý do.

---

### User Story 4 - Học tiếng từ video mẫu (Priority: P2)

Khi học phong cách mới, việc học tiếng tự chạy như một phần của học phong cách; với phong cách đã có, người dùng chạy riêng phần tiếng khi video mẫu còn trên máy. Xưởng tách âm thanh video mẫu thành các lớp, tìm các tiếng động ở cả lớp tiếng động **và** ở lớp giọng ngoài các từ của người kể, đặt tên từng tiếng bằng hai bộ phân loại độc lập, và chỉ giữ tiếng mà hai bộ cùng đồng ý. Mỗi tiếng giữ lại được ghép với từ hoặc hành động gần nhất trong lời kể ("window" → kính vỡ), cùng độ lớn so với giọng và cách nó kết thúc ở điểm cắt. Kết quả là phần "tiếng" của phong cách: tiếng nào hay đi với hành động nào, mật độ tiếng mỗi phút, độ lớn so với giọng, các khoảnh khắc lặng có chủ ý, luật tắt ở điểm cắt. Bước Sound (story 1) dùng phần này để chọn loại tiếng và độ lớn.

**Why this priority**: Làm tiếng theo phong cách thay vì theo cảm nhận (hiến pháp VIII). Nhưng story 1 vẫn chạy được với luật mặc định khi phong cách chưa có phần tiếng.

**Independent Test**: Chạy học tiếng trên mẫu `references/voice-check`: tìm ra cả 5 tiếng đã kiểm bằng tay (kính vỡ ở "window", lặng ≤ −50 dB ở "goes silent", đám đông reo ở "people cheer" tắt trong ≤ 0,1 s quanh điểm cắt, tiếng bóng, bọt nước bể cá), mỗi tiếng có hai nhãn đồng ý và mốc lệch ≤ 0,25 s; không tiếng nào chỉ một bộ phân loại đồng ý được ghi là "tin được".

**Acceptance Scenarios**:

1. **Given** một video mẫu, **When** học tiếng, **Then** mỗi tiếng tìm được có mốc, độ dài, lớp tìm thấy (tiếng động hay giọng ngoài lời), nhãn của từng bộ phân loại, và trạng thái "tin được" chỉ khi hai nhãn đồng ý.
2. **Given** tiếng đám đông nằm trong lớp giọng nhưng ngoài các từ của người kể, **When** học tiếng, **Then** tiếng đó vẫn được tìm và phân loại.
3. **Given** một đoạn gần như im hẳn sau lời kể, **When** học tiếng, **Then** đoạn đó được ghi là "lặng có chủ ý" kèm mức dB và từ đi kèm.
4. **Given** một tiếng chạm điểm cắt shot, **When** học tiếng, **Then** cách nó kết thúc (tắt ngay hay tắt dần, thời gian) được ghi.
5. **Given** học xong, **When** kiểm máy và repo, **Then** âm thanh và các lớp tách ra của video mẫu chỉ nằm trên máy (thư mục tham chiếu, ngoài git); phần tiếng của phong cách chỉ chứa số đo, nhãn và mốc, không chứa âm thanh của video mẫu; không tiếng nào của video mẫu được dùng trong phim.
6. **Given** học ở dịch vụ online (giai đoạn 2), **When** học xong, **Then** âm thanh và các lớp tách ra bị xoá cùng video theo luật hiện có.

---

### Edge Cases

- **Phim web (bộ máy trang)**: không đổi; giữ cách trộn hiện có. 037 chỉ cho phim AE.
- **Phong cách chưa có phần tiếng**: bước Sound dùng luật mặc định (mật độ, độ lớn so với giọng, tắt ở điểm cắt) và ghi rõ trên trang là đang dùng mặc định.
- **Kho tiếng chưa được chỉ** (chưa có thư mục Sonniss): bước Sound báo rõ thiếu kho và cách chỉ thư mục; nếu có khoá Freesound thì vẫn lấp được bằng tiếng CC0; nếu không có gì thì mọi hành động là "missing sound" (để trống, không có tiếng tổng hợp thay), bản trộn chỉ có giọng và nhạc, và trang nói rõ.
- **Thư mục kho bị dời hoặc ổ ngoài chưa cắm**: phim đã chọn tiếng vẫn mở được danh sách; trộn lại báo tiếng nào không đọc được.
- **Hai tiếng chồng nhau quá dày** (nhiều chuyển động trong 0,2 s): giữ theo mật độ tối đa của phong cách, bỏ tiếng ít quan trọng hơn và ghi lý do.
- **Tiếng Freesound bị gỡ hoặc đổi giấy phép sau khi tải**: bản đã tải giữ nguyên giấy phép lúc tải (đã ghi); không tải lại tự động.
- **Một bộ phân loại không chạy được** (thiếu mô hình): học tiếng báo rõ, không ghi tiếng nào là "tin được" chỉ bằng một bộ.
- **Video mẫu không có lời kể**: vẫn tìm và phân loại tiếng; không ghép được với từ thì ghép với shot.
- **Giọng đọc lại sau khi Sound đã duyệt**: Sound chuyển "Must run again" (theo đồ thị phụ thuộc của 035).
- **Phim AE tắt điểm Sound**: bản Sound vẫn được làm và trang vẫn sửa được, nhưng không dừng ở đó.

## Requirements *(mandatory)*

### Functional Requirements

**Danh sách tiếng theo shot**
- **FR-001**: Với phim AE, bước Sound MUST lập danh sách tiếng cho từng shot từ kịch bản, lời đọc đã duyệt và các chuyển động có mốc của shot.
- **FR-002**: Mỗi tiếng trong danh sách MUST có: shot, hành động (tên), chuyển động mà nó gắn vào (nếu có), tiếng được chọn (mục trong kho), độ lệch so với mốc chuyển động, độ dài, độ lớn so với giọng, cách kết thúc ở điểm cắt, và nguồn của lựa chọn (tự động hay người dùng).
- **FR-003**: Mốc của tiếng MUST được tính từ mốc chuyển động của shot và thời lượng shot hiện hành (nguồn duy nhất của 035), không phải mốc tuyệt đối gõ tay.
- **FR-004**: Khi thời lượng shot đổi, chạy lại Sound MUST tính lại mọi mốc; tiếng của chuyển động bị cắt mất MUST bị bỏ kèm lý do hiện trên trang.
- **FR-005**: Tiếng kéo dài chạm điểm cắt MUST kết thúc theo luật của phong cách (hoặc mặc định), trừ khi được đánh dấu kéo qua cắt.
- **FR-005a**: Người dùng MUST bật hoặc tắt tiếng động cho từng shot. Shot bị tắt MUST không có tiếng động nào trong bản trộn và MUST NOT nhận tiếng mới (kể cả tiếng Claude tự đặt). Các tiếng đã có của shot đó MUST được giữ lại (hiện "sound off") và trở lại khi bật shot. Giọng, nhạc và khoảnh khắc lặng không bị ảnh hưởng.
- **FR-006**: Khoảnh khắc lặng có chủ ý MUST hạ mọi lớp (kể cả nhạc) về mức lặng của phong cách trong khoảng đó.
- **FR-007**: Hành động không tìm được tiếng (cả kho trên máy lẫn Freesound) MUST để trống và được ghi "missing sound" kèm từ khoá đã tìm; MUST NOT thay bằng tiếng tổng hợp; bước Sound MUST chạy xong cho các tiếng còn lại.
- **FR-008**: Bản trộn Sound MUST gồm giọng, nhạc hiện có của phim và các tiếng theo shot; độ lớn và phần trăm lặng của bản trộn MUST được bước kiểm phim hiện có đo như với mọi bản trộn.
- **FR-009**: Không tiếng nào từ âm thanh của video tham chiếu được đưa vào bản trộn của phim.

**Kho tiếng**
- **FR-010**: Người dùng MUST chỉ được một hay nhiều thư mục trên máy chứa gói Sonniss GDC; xưởng MUST lập mục lục mọi tệp tiếng đọc được (tên, loại, độ dài, nguồn, giấy phép) và liệt kê riêng tệp hỏng.
- **FR-011**: Lập lại mục lục MUST chỉ đọc các tệp mới hoặc đã đổi.
- **FR-012**: Tìm tiếng cho một hành động MUST dùng được cả tên, loại và mô tả của tiếng trong mục lục; kết quả MUST xếp theo độ hợp.
- **FR-013**: Khi kho trên máy thiếu tiếng và người dùng đã nhập khoá Freesound của họ, bước Sound MUST tự tìm trên Freesound, chỉ xét và tải tiếng có giấy phép CC0, lưu vào kho trên máy kèm số hiệu, người đăng, đường dẫn và giấy phép lúc tải.
- **FR-013a**: Tiếng Sonniss MUST chỉ được dùng trong phim của chủ xưởng (app trên máy và Host/Client cùng nhóm). Với việc của khách ở dịch vụ online, bước Sound MUST chỉ xét tiếng Freesound CC0; tiếng Sonniss MUST NOT được chọn, phát thử hay gửi cho khách.
- **FR-013b**: Mục lục của gói Sonniss MUST chỉ lấy từ tên tệp, thư mục và metadata trong tệp; MUST NOT cho bất kỳ mô hình AI nào xử lý hay học từ âm thanh Sonniss (giấy phép Sonniss cấm dùng cho AI). Chỉ tên và mô tả dạng chữ của mục tiếng được đưa cho Claude.
- **FR-014**: Khoá Freesound MUST được nhập và lưu như khoá ElevenLabs (specs/036): không vào repo, không hiện lại đầy đủ, không gửi cho dịch vụ khác.
- **FR-015**: Tệp tiếng của kho MUST NOT vào git và MUST NOT nằm trong bộ cài app.
- **FR-016**: CREDITS của mỗi phim MUST có một dòng cho mỗi tiếng đã dùng (nguồn, giấy phép); CREDITS chung của xưởng MUST ghi Sonniss GDC và Freesound (CC0) là nguồn tiếng.

**Học tiếng từ video mẫu**
- **FR-017**: Học tiếng MUST tách âm thanh video mẫu thành lớp, và tìm tiếng động ở lớp tiếng động và ở lớp giọng ngoài các từ của người kể.
- **FR-018**: Mỗi tiếng tìm được MUST được đặt tên bởi hai bộ phân loại độc lập; tiếng MUST chỉ được ghi "tin được" khi hai nhãn đồng ý (theo bảng tương ứng nhãn ghi trong kết quả học). Tiếng không đồng ý MUST được giữ ở danh sách "chưa chắc" để xem lại, không dùng làm luật.
- **FR-019**: Mỗi tiếng tin được MUST được ghép với từ hoặc hành động gần nhất trong lời kể (hoặc với shot khi không có lời), kèm độ lớn so với giọng và cách kết thúc ở điểm cắt.
- **FR-020**: Học tiếng MUST tìm các khoảnh khắc lặng có chủ ý (mức dB, độ dài, từ đi kèm).
- **FR-021**: Kết quả học MUST lưu thành phần "tiếng" của phong cách (bảng hành động → loại tiếng, mật độ tiếng mỗi phút, độ lớn so với giọng, khoảnh khắc lặng, luật tắt ở điểm cắt), mỗi luật kèm bằng chứng (mốc trong video mẫu), theo khung 11 mục của phong cách.
- **FR-022**: Âm thanh và các lớp tách ra của video mẫu MUST chỉ nằm trên máy, ngoài git; phần tiếng của phong cách MUST chỉ chứa số đo, nhãn và mốc. Ở dịch vụ online, chúng MUST bị xoá khi học xong theo luật hiện có.
- **FR-023**: Học tiếng MUST tự chạy trong học phong cách cho phong cách mới, và MUST chạy được riêng cho một phong cách đã có khi video mẫu của phong cách còn trên máy.

**Điểm duyệt Sound**
- **FR-024**: Điểm Sound (tên điểm duyệt hiện có `mix`) của phim AE MUST hiện dải thời gian (shot, câu thoại, tiếng theo shot có nhãn) và lưới shot; bấm một shot MUST phát clip nháp của shot đó với bản trộn Sound.
- **FR-025**: Người dùng MUST đổi được tiếng (ít nhất 3 tiếng thay thế cùng loại khi kho có, nghe thử được), dời mốc, đổi độ lớn, xoá và thêm tiếng; sửa MUST được ghi là của người dùng và giữ qua các lần Sound chạy lại.
- **FR-026**: Sau một sửa, bản trộn MUST được làm lại; các đoạn không bị sửa MUST giống hệt trước.
- **FR-027**: "Send notes to Claude" MUST gửi mọi ghi chú đang mở của bước Sound trong một lượt; việc sửa chạy nền trên app; Claude MUST chỉ sửa tiếng của shot có ghi chú và trả lời từng ghi chú; bước Sound trở về chưa duyệt.
- **FR-028**: Khi điểm Sound bật, lệnh dựng bản đẹp MUST bị từ chối khi Sound chưa được duyệt, kèm lý do. Agent MUST NOT tự duyệt Sound.
- **FR-029**: Đọc lại giọng, đổi thời lượng shot hoặc sửa shot ở Animatic sau khi Sound đã duyệt MUST đánh dấu Sound "Must run again" (theo 035); sửa ở Sound MUST chỉ đánh dấu Final render.

### Key Entities

- **Mục tiếng (Sound entry)**: một tệp tiếng trong kho trên máy; tên, loại, mô tả, độ dài, nguồn (Sonniss GDC năm nào, hoặc Freesound số hiệu, người đăng, đường dẫn), giấy phép lúc lấy về, đường dẫn trên máy.
- **Kho tiếng (Sound library)**: các thư mục người dùng chỉ ra cùng mục lục; thuộc máy (của chủ xưởng), không thuộc phim hay repo.
- **Tiếng trong shot (Shot sound cue)**: thuộc một shot; hành động, chuyển động gắn vào, mục tiếng, độ lệch, độ dài, độ lớn, cách kết thúc ở cắt, nguồn lựa chọn (tự động/người dùng), trạng thái (đặt được, bị bỏ kèm lý do, missing sound).
- **Danh sách tiếng của phim (Sound plan)**: mọi tiếng trong shot của phim, ứng với một bộ thời lượng shot; sinh ra bản trộn Sound.
- **Tiếng học được (Learned sound event)**: thuộc một video mẫu; mốc, độ dài, lớp tìm thấy, hai nhãn, trạng thái tin được/chưa chắc, từ hoặc shot ghép, độ lớn so với giọng, cách kết thúc ở cắt.
- **Phần tiếng của phong cách (Style sound profile)**: luật rút từ các tiếng học được (hành động → loại tiếng, mật độ, độ lớn, lặng có chủ ý, tắt ở cắt), mỗi luật kèm bằng chứng.
- **Ghi chú Sound (Sound note)**: thuộc một shot; nội dung, trạng thái mở/đã trả lời, câu trả lời của Claude, lượt sửa.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Với `ae-sleepless-test`, bước Sound đặt tiếng cho ≥ 90% các chuyển động có tên trong shot mà kho có tiếng hợp; 100% tiếng đặt được lệch ≤ 1 khung so với mốc chuyển động.
- **SC-002**: Đổi thời lượng một shot ở Animatic rồi chạy lại Sound: 100% mốc tiếng được tính lại đúng (≤ 1 khung), không mốc nào phải sửa tay; tiếng bị bỏ đều có lý do.
- **SC-003**: Học tiếng trên `references/voice-check` tìm đủ 5/5 tiếng đã kiểm bằng tay với mốc lệch ≤ 0,25 s, và 0 tiếng chỉ một bộ phân loại đồng ý được ghi "tin được".
- **SC-004**: 100% tiếng tải từ Freesound có giấy phép CC0; 100% tiếng dùng trong một phim có dòng trong CREDITS của phim.
- **SC-005**: 0 tệp âm thanh của video tham chiếu hoặc của kho tiếng trong git và trong bộ cài; 0 mẫu âm thanh của video tham chiếu trong bản trộn của phim; 0 tiếng Sonniss trong việc của khách online; 0 lần âm thanh Sonniss được đưa vào mô hình AI khi lập mục lục (đều có test tự động).
- **SC-006**: Một sửa ở trang Sound (đổi, dời, xoá một tiếng) cho bản trộn mới trong ≤ 30 s với phim 30 s; phần âm thanh ngoài đoạn sửa giống hệt từng mẫu, với đoạn sửa = [mốc đầu − 60 ms, kết thúc + 60 ms] của tiếng trước và sau khi sửa.
- **SC-007**: Lập mục lục 10.000 tệp tiếng xong trong ≤ 15 phút lần đầu và ≤ 1 phút khi lập lại không có tệp mới.
- **SC-008**: 100% lệnh dựng bản đẹp bị từ chối khi điểm Sound bật mà chưa duyệt, có test tự động.
- **SC-009**: Bản trộn Sound của phim thử qua bước kiểm phim hiện có (độ lớn tổng, giọng nổi trên nền, phần trăm lặng) không kém bản trộn viết tay hiện nay.

## Assumptions

- Chỉ áp dụng cho phim After Effects; phim web giữ cách trộn hiện có.
- Xây trên 035 (thời lượng shot là nguồn duy nhất, đồ thị phụ thuộc, cơ chế ghi chú và việc sửa chạy nền của Animatic), 034 (ghim ghi chú) và 032 (bộ dựng AE). Code của 037 dùng các phần của 035 sau khi 035 được merge; thứ tự merge dự kiến 035 → 037.
- Người dùng tự tải các gói Sonniss GDC (họ tự đồng ý điều khoản Sonniss) vào một thư mục trên máy; xưởng (sản phẩm) không tải hộ và không phân phối lại tiếng của gói. Kho thuộc máy chạy xưởng (máy Host ở chế độ Host/Client). Máy phát triển dùng gói 2026 và 2024 ở `E:\SoundLibrary\Sonniss` (người dùng đồng ý giấy phép bản 2.0 ngày 2026-11-25). Tải bằng script không được (trang chính có bước kiểm Cloudflare, mirror Google Drive hết hạn mức, mirror Feral lỗi 504), nên người dùng tải bằng trình duyệt; tới lúc đó test dùng kho thử nhỏ.
- Giấy phép Sonniss GDC 2.0: dùng thương mại không cần ghi tên; cấm cung cấp tiếng gốc hay đã sửa cho người khác (kể cả như đầu ra của dịch vụ); cấm dùng cho AI. CREDITS vẫn ghi Sonniss là nguồn để minh bạch.
- Người dùng tự tạo khoá Freesound miễn phí. Không có khoá thì không lấp chỗ thiếu.
- Nhạc nền giữ như hiện có (của phim hoặc của bộ kit phong cách); 037 chỉ thêm tiếng động, tiếng nền theo shot và khoảnh khắc lặng.
- Bước Sound dùng Claude (Opus 5.5, như mọi lệnh gọi Claude của xưởng) để đọc kịch bản và chuyển động rồi lập danh sách hành động; việc chọn tiếng, đặt mốc và trộn không cần Claude.
- Các chuyển động của shot đọc được từ mã dựng shot của phim (tên và mốc keyframe); chuyển động không có mốc đọc được thì gắn tiếng theo câu thoại.
- Luật mặc định khi phong cách chưa có phần tiếng: lấy từ mẫu đã kiểm và phim thử (mật độ, độ lớn so với giọng, tắt ngay ở điểm cắt).
- Một người dùng (chủ xưởng) duyệt; không có phân quyền duyệt riêng.
