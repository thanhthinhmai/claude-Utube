# Research: Bộ code mẫu cho phong cách học được (022)

Mỗi mục: **Quyết định**, **Lý do**, **Đã cân nhắc**.

## R1. Trang phim với tới bộ dựng thế nào (FR-001)

**Quyết định**: bộ dựng nằm ở `my-styles/<slug>/kit/` và được **chép** vào `films/<tên>/kit/` bằng lệnh mới `sh bin/studio kit use <tên> [--style S]`:
- phong cách lấy từ `--style`, nếu không có thì từ `channel.json` của phim; phong cách không có `kit/` thì thoát 2;
- chép cả thư mục trừ `test/`, ghi `kit/.from` (`{"style", "sha256", "at"}`, dấu băm tính trên các tệp đã chép);
- đã có `kit/` cùng dấu băm thì không làm gì; khác dấu băm thì chỉ chép đè khi có `--update` (phim đang làm không bị đổi ngầm).

Trang phim nạp `./kit/film.js`. Phim mẫu: `demo/build.sh` ghép `demo/` và `../kit/` vào `$OUT/page/` rồi dựng thư mục đó.

**Lý do**: `core/render/serve.mjs` của thư viện chỉ trả tệp trong gốc thư viện, hoặc trong thư mục phim gắn ở `/@film/`; đường dẫn ra ngoài bị 403. Không được sửa thư viện (VI). Bản chép còn giữ cho phim dựng lại đúng như lúc làm.

**Đã cân nhắc**: liên kết mềm (không theo được trên Windows, trong container của worker và trong bộ cài); để Claude tự `cp -r` (không ghi được phiên bản, dễ chép sai chỗ trong app và worker); thêm thư mục thứ hai vào máy chủ (phải sửa thư viện).

## R2. Hình dạng của bộ dựng (FR-001, SC-005)

**Quyết định**: các module ES thuần, không bước build, mỗi phần một tệp (xem plan). Trang phim viết một bảng cảnh `SCENES` và gọi `film({ scenes, cues, … })`; `film.js` lo mọi việc của hợp đồng trang (contracts/kit-api.md). Một cảnh là một đối tượng ≤ 15 dòng: `set`, `cam`, `cast`, `crowd`, `gfx`, `mood`, `dur`.

Phần thuần (`film.js` tính thời gian, `SHOTS`, `CARDS`, kiểm tên theo `catalog.json`) không import three.js, để `node --test` chạy được. Tên lạ trong bảng cảnh làm `film()` ném lỗi và không đặt `READY`: `qc plan` dừng ngay, không lặng lẽ vẽ sai.

**Lý do**: SC-005 đòi trang phim không viết lại nhân vật, ánh sáng, hậu kỳ hay đồ hoạ. Khung chứng minh dài 208 dòng cho một cảnh; mô tả bằng dữ liệu đưa 220 cảnh xuống khoảng 2.000–3.000 dòng bảng cảnh.

**Đã cân nhắc**: lớp đối tượng kiểu "scene graph" riêng (thêm lớp trừu tượng, trái V); một tệp lớn duy nhất (khó đọc và khó chép từng phần khi sửa).

## R3. Nhân vật có khớp (FR-002)

**Quyết định**: cây `THREE.Group` theo khớp: hông → thân → cổ → đầu; vai → cánh tay trên → khuỷu → cẳng tay → bàn tay tròn; hông → đùi → gối → cẳng chân → bàn chân. Mỗi đoạn là capsule bo tròn, nhựa mờ (`MeshStandardMaterial`, roughness 0,9). Đầu cầu ≈ 1/3 chiều cao.
- Mặt là texture canvas trên nửa trước của đầu: 8 biểu cảm (`dot`, `half`, `wow`, `happy`, `blank`, `angry`, `sad`, `sweat`), không mũi tai.
- Hoodie: thân áo, mũ trùm (nửa xuyến sau gáy) và hai dây rút; biến thể tóc (`bald`, `short`, `bun`, `curly`), mũ (`cap`, `beanie`), kính.
- Tư thế là bảng góc khớp (`stand`, `sit`, `walk`, `hold-phone`, `hold-book`, `hold-bag`, `hold-cup`, `hold-paper`, `point`, `cheer`, `shrug`); `turn` và `tilt` của đầu cộng thêm. `walk` là chu kỳ theo `t`. Tư thế `sit` đặt hông đúng chiều cao ghế (sửa vòng 1 của khung chứng minh).
- Đồ cầm tay gắn vào khớp bàn tay; điện thoại có màn sáng yếu và viền nắng ấm thay cho ánh rọi mặt (vòng 8).

**Lý do**: đúng các vòng 1, 5, 6, 8 của khung chứng minh và mục 4 của `STYLE.md`.

**Đã cân nhắc**: mô hình có xương (`SkinnedMesh`) tải về: trái giả định "mọi hình dựng bằng code" và cần tài sản bên thứ ba; ống thẳng không khớp: chính là lỗi vòng 6.

## R4. Đám đông hàng nghìn người và bộ nhớ đệm bối cảnh (FR-003, SC-003)

**Quyết định**: ba mức theo khoảng cách tới máy:
- **gần** (≤ 12 người, ≤ 6 m): nhân vật đủ khớp của R3;
- **vừa** (6–25 m): `InstancedMesh` cho 4 phần (thân áo, đầu, tóc hoặc mũ, chân), mỗi phần một lần vẽ cho mọi người; màu theo từng người (`instanceColor`);
- **xa** (> 25 m): `Points` có kích thước theo khoảng cách, màu áo.

Người phân biệt bằng màu áo (bảng màu của phong cách, `mulberry` có hạt giống theo cảnh) rồi tóc hoặc mũ. Chuyển động: đứng im hoặc cùng một nhịp nhún nhẹ theo `t` (mục 5 của `STYLE.md`).

Mỗi bối cảnh dựng một lần rồi giữ trong bộ đệm (tối đa 4 bối cảnh, bỏ cái dùng lâu nhất); `render(t)` tìm cảnh theo `t`, bật bối cảnh và đặt nhân vật theo `t`, nên tất định khi gọi theo thứ tự bất kỳ.

**Lý do**: 1.000 người đủ khớp là khoảng 30.000 lần vẽ, không giữ được 60 fps; ba mức đưa cảnh 1.000 người về khoảng vài chục lần vẽ. Bộ ghi chia đoạn 10 s và có thể mở lại trang giữa chừng (specs/019), nên mọi trạng thái phải tính lại được từ `t`.

**Đã cân nhắc**: hình người là sprite phẳng ở mức vừa (lộ khi máy chéo, trái "không phẳng" của phong cách); dựng lại bối cảnh mỗi lần đổi cảnh (chậm với cảnh lặp lại nhiều lần).

## R5. Ánh sáng và hậu kỳ mặc định (FR-005, SC-001, SC-002)

**Quyết định**: `stage.js` mang đúng bộ số của khung chứng minh đã đạt: ACES, `toneMappingExposure` 0,8, bóng mềm PCF, sương tím (`#2a1e40`, 8–24 m), `makePost` của thư viện (DOF, bloom 0,3), vignette và bão hoà của lần sửa vòng 3–4, viền nắng ấm, trần và cuối phòng tự sáng nhẹ (vòng 9). Mỗi số ghi trong `kit/GRADE.md` kèm số đo đối chiếu (độ sáng trung vị 0,26, khoảng 0,22–0,29; bão hoà 0,35, khoảng 0,32–0,41). Mỗi bối cảnh và mỗi `mood` (`alarm`, `night`, `lilac`) chỉ được đổi số trong khoảng của phong cách, không đổi mặc định.

Lớp WebGL được chép sang một canvas 2D mỗi khung (như khung chứng minh), vì ảnh chụp của WebGL phần mềm có thể trống.

**Lý do**: SC-002 đòi cảnh dựng lại bố cục khung gốc đạt ngưỡng `learn compare` ngay lần đầu; cách chắc nhất là dùng lại số đã đạt.

**Đã cân nhắc**: đặt lại số theo cảm nhận cho từng bối cảnh (lặp lại 9 vòng sửa).

## R6. Nhân vật chính của kênh (FR-015, FR-014)

**Quyết định**: `channel.json` có trường `hero`:

```json
{"hoodie": "#d9b23a", "strings": "#ffffff", "hair": "bald", "hat": null, "glasses": false}
```

- Đặt bằng `channel set <kênh> hero hoodie=#d9b23a hair=bald …` (chỉ đổi các khoá nêu); `channel attach` chép `hero` vào bản chụp `channel.json` của phim (`film.hero`).
- Bộ dựng đọc `./channel.json` của phim; không có thì dùng mặc định trong `catalog.json` và trang in một dòng cảnh báo vào console, `kit use` in gợi ý `channel set`.
- Kiểm khác nhân vật của kênh tham chiếu: `kit/catalog.json` có `avoid_hero` (áo xanh nhạt, đo từ bằng chứng của phong cách, không ghi tên kênh). `channel set` và `kit use` từ chối khi áo cùng nhóm màu: khoảng cách màu trong không gian Lab ΔE < 25 so với áo cần tránh. Ngưỡng 25 không có số đo (khoảng cách mà mắt thấy rõ là hai màu khác nhóm); người dùng duyệt ngày 2026-11-14.

**Lý do**: người dùng chốt nhân vật cố định theo kênh (Clarifications). Kênh mặc định cũng đầu trọc như nhân vật của kênh tham chiếu, nên khác biệt nằm ở màu áo và phải được kiểm bằng số.

**Đã cân nhắc**: lưu trong phong cách (một phong cách dùng cho nhiều kênh sẽ có cùng nhân vật chính); mỗi phim tự chọn (người dùng đã loại).

## R7. Đồ hoạ và khai báo cho các tầng kiểm (FR-006)

**Quyết định**: `graphics.js` vẽ trên canvas 2D phủ trên khung hình, trong vùng hình (giữa hai dải đen 6,4%). Chữ in hoa IM Fell English (OFL, có trong `core/fonts`), màu kem `#f3e3b0` hoặc vàng nhạt, phát sáng nhẹ, giãn chữ rộng. Mỗi đồ hoạ có chữ được `film.js` tự thêm vào `window.CARDS` với thời gian của nó; pill số đếm lên theo ease-out và giữ. Khi `window.CLEAN` bật (chụp thumbnail), không vẽ đồ hoạ có chữ và phụ đề.

Phụ đề do `film.js` vẽ từ `cues` (hoặc `cues.json`) và xuất `window.CUES`, theo contracts/film-page.md của specs/020.

**Lý do**: tầng 1 và tầng 2 cần biết mọi chữ trên hình; tự sinh từ bảng cảnh thì không lệch.

**Đã cân nhắc**: chữ dựng bằng mesh 3D (khó đọc ở cỡ nhỏ, khó khai báo vùng chữ).

## R8. Style-learn: STRUCTURE.md và `learn save` (FR-012, FR-013)

**Quyết định**:
- `save` chép từ `references/<set>/style/` theo **danh sách cho phép**: `STYLE.md`, `EVIDENCE.md`, `style.json`, `STRUCTURE.md`, `shots.json` (nếu có), `styleframe/` (các tệp mã nguồn) và `styleframe.jpg`. Tệp khác bị bỏ và in một dòng `skipped: <tên>`. Khi `--update`, `kit/`, `demo/` và các tệp phim mẫu của phong cách cũ được giữ.
- `STRUCTURE.md` đi qua `check-names` như `STYLE.md`.
- SKILL.md, bước viết mục 11: nếu phong cách học cho một kênh có quyết định theo cấu trúc tham chiếu (`channel show` của kênh đó), viết `STRUCTURE.md` (chỉ màn, tỉ lệ, mốc, nhịp; không câu chữ) và mục 11 trỏ tới đó; không thì giữ luật "khác kênh gốc".

**Lý do**: lần học lại 2026-11-13 phải xoá tay 4 tệp làm việc; danh sách cho phép chặn cả loại tệp mới sau này.

**Đã cân nhắc**: danh sách chặn (`*.log`, `review-*.md`, `.job*`): sót loại mới.

## R9. Phim mẫu dài và 60 fps (FR-010, FR-011, SC-004)

**Quyết định**: phim mẫu làm theo luồng làm phim của `CLAUDE.md` trong `films/dusk-demo/` (kênh `dusk-hypothetical`, ≈ 630 s, kịch bản theo `STRUCTURE.md`), ghi bằng `sh bin/studio render dusk-demo --fps 60` trên GPU. Đạt các tầng thì chép trang, bảng cảnh, `lines.json`, `mix.py` vào `demo/` (không chép `kit/`, `build.sh` ghép lại từ `../kit`); `build.sh` có `LIB=` ở đầu, tạo giọng, ghép trang, dựng ở 60 fps, trộn và ghép tiếng. `test.mp4` ngoài git; `test.jpg` là một khung của phim.

Mốc màn đo trên `SCRIPT.md` theo thời gian của giọng đọc (`narration.json`), so với `STRUCTURE.md` (±5 điểm %). Số bối cảnh, cỡ cảnh và góc máy đo từ `SHOTS` và nhãn của `qc shots`.

**Lý do**: Clarifications chốt phim mẫu đủ dài và là phim thử của US2: một lần chạy cho cả US2 và US4. Phim làm trong `films/` thì đi qua đủ các tầng kiểm có sẵn.

**Đã cân nhắc**: phim mẫu ngắn 30–60 s (người dùng đã loại); dựng phim mẫu thẳng trong `demo/` (không qua được các lệnh kiểm vốn đọc `films/<tên>/`).
