# Template: Dusk Hypothetical

Bộ tham chiếu: `dusk-hypothetical-3` · 10 video, dài đủ (6.654 s, 2.192 cảnh) · học ngày 2026-11-13, đo tay nghề ngày 2026-11-17 · luật hình theo 8 phim 3D, nhịp và âm thanh theo cả 10 phim.

Đây là **cách làm của xưởng**: mỗi thành phần ghi cách dựng, số đo kèm khoảng, khung mẫu làm bằng chứng, điều nên và không nên làm, và tên gọi trong bộ dựng (`kit/`). Bằng chứng trỏ tới ô của bảng ảnh cảnh (`vNN_shots_k.jpg#ô`), dải khung (`vNN/strips/Sxxx.jpg#k`) hay khung lẻ (`vNN/evidence/<tên>.jpg`) trong `references/dusk-hypothetical-3/profile/`. Các ảnh này ở ngoài git. Số đo lấy từ `profile/craft-summary.json`, `profile/summary.json` và ba báo cáo học (`visual §n.m` theo cách đánh số ở đầu `STYLE.md`). Không chép câu chuyện, câu chữ, nhân vật hay khung cụ thể nào của kênh mẫu.

## 1. Khuôn mặt và biểu cảm

Đầu là một khối cầu trắng ngà, không mũi, không tai. Nét mặt nhỏ và nằm thấp trên khối cầu, nên phần trán trống rất rộng. Mắt là chấm đen nhỏ, hoặc nét cung mảnh khi nhắm hay cười, hoặc mí trên dày sụp xuống một nửa (vẻ đắc ý, chán, nghi ngờ). Mày ngắn, chỉ hiện khi tức giận hay lo. Miệng là một nét cung nhỏ, chữ "o" hoặc hình chữ D. Nhân vật nữ có 2–3 sợi mi và má hồng hình bầu dục. Mặt diễn bằng mí, mày và miệng, không bằng chi tiết. Cận rất sát (ECU) thường quay một đồ vật chứ không phải mặt.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| chiều cao đầu so với cả người | 0,35 | 0,32–0,39 | visual §5.2 (10 khung toàn thân) |
| ECU quay đồ vật thay cho mặt | 4/8 | 3–5 trên 8 ô ECU được xem | craft-notes (bảng mặt 2026-11-17) |
| biểu cảm hay gặp nhất ở cận | mí nửa | mí nửa, chấm, cung cười, chữ o | visual §9.2–3 |

Bằng chứng: v02_shots_3.jpg#43, v05_shots_1.jpg#44, v10_shots_1.jpg#5, v04_shots_1.jpg#6, v04_shots_4.jpg#39, v07_shots_2.jpg#32, v06_shots_2.jpg#6, v07_shots_4.jpg#28
Nên làm: nét mặt nhỏ, đặt ở nửa dưới khối cầu; mắt chấm hoặc cung mảnh; mí trên dày cho vẻ đắc ý; mày chỉ hiện khi cần; má hồng và mi cho nhân vật nữ; ECU dành cho đồ vật kể chuyện (điện thoại, thẻ, bánh xe số).
Không nên làm: mắt to tròn kiểu hoạt hình, mắt elip phẳng, lông mày khối đen thường trực, răng, mũi; nét mặt to chiếm cả đầu; ECU chính diện giữa khung chỉ để quay mặt.
Trong bộ dựng: `figure.js → face(name)`, `catalog.faces` (`dot`, `half`, `wow`, `happy`, `blank`, `angry`, `sad`, `sweat`), `cast[].blink`, `cam: 'ecu'` cùng `gfx`/đồ cầm tay

## 2. Thân và trang phục

Một kiểu thân cho mọi người. Cổ là que mảnh. Áo hoodie ngắn, thuôn dần xuống, có mũ trùm sau gáy. Chân trắng mảnh như que, tay là quả cầu trắng. Đầu rộng hơn vai rõ rệt, nên ở đám đông cái đầu vẫn được thấy trước. Nhân vật phụ phân biệt bằng màu áo, rồi tới tóc hoặc mũ, rồi một đồ vật trên tay. Cận và trung cảnh hầu như luôn có đồ cầm tay.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| bề rộng đầu so với vai | 1,4 | 1,3–1,5 | visual §5.3 |
| chiều cao đầu so với cả người | 0,35 | 0,32–0,39 | visual §5.2 |
| cách phân biệt nhân vật phụ | 3 bậc | màu áo → tóc/mũ → đồ vật | visual §9.9 |

Bằng chứng: v01_shots_3.jpg#20, v02_shots_4.jpg#20, v06_shots_4.jpg#20, v10_shots_6.jpg#39
Nên làm: hoodie ngắn thuôn có mũ trùm và tay áo rõ; chân que trắng; tay cầu; một đồ vật trên tay ở cận và trung cảnh; màu áo bão hoà nổi trên nền tím.
Không nên làm: thân hình bao tải, vạch trắng dọc thân; tay chân to; trang phục chép từ nhân vật chính của kênh mẫu (áo xanh nhạt, đầu trọc).
Trong bộ dựng: `figure.js → makeFigure`, `catalog.hair`, `catalog.hats`, `cast[].hold`, `channel.json → hero`

## 3. Bố cục theo cỡ cảnh

Chủ thể nằm giữa khung. Ô nét nhất nằm ở hai cột giữa (trên lưới 4 cột) ở phần lớn cảnh của mọi cỡ. Nhân vật chính hay đứng nhỏ trong một không gian lớn đối xứng (khán phòng, phòng tập, sân) để thấy được quy mô. Bố cục lệch hẳn sang mép gặp nhiều nhất ở ECU và cảnh rất rộng. Cảnh hai người dùng qua vai: một đầu mờ to choán một phần ba khung ở một bên.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| ECU lệch mép | 0,256 | 0,08–0,26 (theo cỡ) | template.json → framing.by_scale.ecu.off_centre |
| cảnh rất rộng lệch mép | 0,202 | 0,08–0,26 (theo cỡ) | template.json → framing.by_scale.huge.off_centre |
| cận ở hai cột giữa | 0,92 | 0,74–0,92 (theo cỡ) | template.json → framing.by_scale.cu.middle |
| trung cảnh ở hai cột giữa | 0,881 | 0,74–0,92 (theo cỡ) | template.json → framing.by_scale.med.middle |

Bằng chứng: v04_shots_4.jpg#30, v04_shots_3.jpg#7, v09_shots_3.jpg#1, v10_shots_1.jpg#21, v01_shots_3.jpg#20
Nên làm: đặt chủ thể ở giữa hoặc hơi lệch trong hai cột giữa; cho nhân vật nhỏ trong không gian lớn có lưới đồ vật; cảnh qua vai có đầu mờ ở tiền cảnh; lệch hẳn sang mép chỉ ở ECU và cảnh rất rộng.
Không nên làm: dồn mọi cận vào chính giữa với nền trống; lệch mép ở mọi cảnh (kênh mẫu không làm vậy); để khung chật không còn không gian quanh nhân vật.
Trong bộ dựng: `camera.js → place`, `frame: 'auto'`, `cam: 'ots'`, `catalog.cams`

## 4. Độ sâu theo cỡ cảnh

Chủ thể luôn nét. Khoảng một phần ba khung mờ: nền ở xa, đám đông phía sau, đèn thành đốm sáng tròn. Cận mờ nhiều hơn cảnh rộng. Tiền cảnh mờ (vai, đầu, lan can) xuất hiện nhiều ở cận và trung cảnh, nhất là cảnh qua vai.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| phần khung nét, cận | 0,5 | 0,42–0,67 | template.json → framing.by_scale.cu.focused_share |
| phần khung nét, trung cảnh | 0,667 | 0,5–0,83 | template.json → framing.by_scale.med.focused_share |
| phần khung nét, ECU | 0,5 | 0,25–0,67 | template.json → framing.by_scale.ecu.focused_share |
| tiền cảnh mờ, cận | 0,253 | 0,08–0,25 (theo cỡ) | template.json → framing.by_scale.cu.foreground_blur |
| tiền cảnh mờ, cảnh rộng | 0,095 | 0,08–0,25 (theo cỡ) | template.json → framing.by_scale.wide.foreground_blur |

Bằng chứng: v09_shots_3.jpg#1, v05_shots_2.jpg#15, v07_shots_2.jpg#1, v06_shots_3.jpg#29, v04_shots_3.jpg#7
Nên làm: lấy nét vào mặt chủ thể; cận và ECU để nền mờ thành đốm sáng; cứ khoảng 1/4 cận và trung cảnh thì có một tiền cảnh mờ; cảnh rộng giữ phần lớn khung nét.
Không nên làm: để cả đám đông phía sau nét căng ở cận; làm mờ cả chủ thể; dùng tiền cảnh mờ ở mọi cảnh rộng.
Trong bộ dựng: `camera.js → place` (`focus`, `aper`), `stage.js → focus`, `cam` có tiền cảnh `fg`

## 5. Ánh sáng

Đèn chính mềm, từ trên và lệch một bên. Đầu có vệt sáng hồng trắng ở phía được chiếu và mép chuyển tím ở phía tối. Có viền sáng (rim) tách đầu khỏi nền. Khoảng một nửa số cảnh có một bên khung sáng hơn rõ, từ trái và từ phải gần như ngang nhau. Màu ấm chỉ đến từ đèn trong cảnh (cửa sổ, dây đèn, đèn bàn, đèn sân), chiếm rất ít diện tích. Không phải "nắng xiên ấm" phủ khắp khung. Góc khung luôn tối do viền tối (vignette).

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| cảnh có một bên sáng hơn rõ | 0,553 | 0,41–0,65 (theo cỡ) | template.json → light.raking |
| diện tích điểm sáng ấm (p25–p75) | 0,0016 | 0–0,0164 | template.json → light.warm_share |
| độ chênh sáng tối p90−p10 (p25–p75) | 0,442 | 0,345–0,549 | template.json → light.range |

Bằng chứng: v01_shots_3.jpg#20, v09_shots_3.jpg#1, v04_shots_1.jpg#29, v05_shots_1.jpg#44, v10_shots_4.jpg#24
Nên làm: đèn chính mềm lệch một bên, đổi bên giữa các cảnh; viền sáng trên đầu; ấm đến từ đèn trong cảnh và nở thành quầng; giữ độ chênh sáng tối vừa phải.
Không nên làm: sáng đều phẳng không có phía tối; phủ nắng cam khắp khung; ánh sáng trắng trung tính mặc định của three.js; sàn sáng hơn nhân vật.
Trong bộ dựng: `stage.js` (key, sun, rim, front), `catalog.moods`, `scene.grade`

## 6. Bối cảnh và đạo cụ kể chuyện

Mỗi phim đi qua khoảng 30 nơi. Một hai nơi "nhà" (lớp, phố, phòng ngủ) được cắt xen với nhiều nơi chỉ xuất hiện một cảnh để minh hoạ một ý. Mỗi nơi được dựng bằng hình khối đơn giản lặp thành lưới (bàn, tủ, ghế khán đài, cửa sổ sáng), cộng một hai đạo cụ kể đúng chuyện của cảnh: bàn chơi bài, máy chụp, bảng đen, rổ bóng. Đạo cụ cũng là cái nhân vật đang cầm.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| số nơi mỗi phim | 29,5 | 18–49 | motion-depth §5.1 |
| một lượt ở một nơi (s) | 4,9 | 4,0–6,3 | motion-depth §5.2 |
| lượt chỉ có một cảnh | 0,56 | — một cảnh là đủ | motion-depth §5.2 |
| cửa sổ sáng trên mặt nhà | 30–60 % | 0,30–0,60 | visual §4.3 |

Bằng chứng: v04_shots_3.jpg#7, v05_shots_2.jpg#15, v10_shots_5.jpg#3, v07_shots_2.jpg#1, v06_shots_4.jpg#20
Nên làm: dựng mỗi nơi bằng lưới đồ vật lặp lại cộng một đạo cụ kể chuyện; đặt đạo cụ trên tay nhân vật ở cận; mở nơi mới bằng cảnh rộng; có ít nhất một đèn trong cảnh.
Không nên làm: đồ vật lặp đều mà không có đạo cụ nào kể chuyện; nền trống; một nơi kéo dài nhiều phút không cắt sang nơi khác.
Trong bộ dựng: `sets/*.js`, `sets/parts.js`, `catalog.sets`, `set: 'custom:<tên>'`

## 7. Đám đông

Đám đông là bản sao của cùng một kiểu người, màu áo và tóc ngẫu nhiên, đứng hay ngồi thành hàng. Số người theo nơi: lớp 10–20, hàng chờ 20–30, khán đài phòng tập 40–100, khán phòng vài trăm, sân vận động hay quảng trường hàng nghìn, xa tới mức chỉ còn chấm màu. Người trong đám đông gần như đứng yên; chỉ nhân vật chính diễn.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| người trong lớp học | 15 | 10–20 | visual §9.11 |
| người trên khán đài | 70 | 40–100 | visual §9.11 |
| cảnh rất rộng có đám đông lớn | 13 % số cảnh | 9–28 % (theo phim) | visual §12.8; summary.json → scale_huge |

Bằng chứng: v04_shots_4.jpg#8, v02_shots_4.jpg#16, v09_shots_2.jpg#36, v10_shots_4.jpg#24, v01_shots_1.jpg#5
Nên làm: đám đông trong hầu hết cảnh rộng; xa thì thu thành chấm màu; đứng yên hoặc cùng nhún nhẹ; màu áo ngẫu nhiên nổi trên nền tối.
Không nên làm: cảnh rộng không có ai; cho cả đám đông diễn tranh với nhân vật chính; đám đông nét căng ở cận.
Trong bộ dựng: `crowd.js → makeCrowd`, `scene.crowd {n, seed}`, `anchors.crowd`

## 8. Thẻ số liệu

Một con số thật được kể bằng một **hình ẩn dụ** vẽ phẳng, không chỉ bằng chữ: não cho trí nhớ, lọ thuỷ tinh cho may mắn tích luỹ, tim kèm đường nhịp cho nhịp tim, bản đồ có đường đi, tờ khảo sát có dòng kẻ. Thẻ nằm trên nền tím có hạt hoặc trên chính cảnh đã làm mờ và tối đi. Chữ in hoa ngắn màu kem, số to. Các phần hiện dần (thanh dâng lên, số đếm lên rồi giữ).

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| cảnh đồ hoạ trọn khung mỗi phút | 1,6 | 4–32 mỗi phim | visual §11 (rules #1) |
| thời gian cảnh đồ hoạ (theo phim) | 9–15 % | 5–26 % | motion-depth §4.9 |
| thanh dâng lên (s) | 1,3 | 1,2–1,4 | motion-depth §2.7 |

Bằng chứng: v01_shots_2.jpg#12, v06_shots_2.jpg#8, v04_shots_3.jpg#46, v05_shots_3.jpg#15, v02_shots_1.jpg#37
Nên làm: mỗi số liệu có một hình ẩn dụ; thẻ trên nền tím có viền tối hoặc trên cảnh mờ; chữ in hoa ngắn; số đếm lên rồi giữ.
Không nên làm: thẻ chỉ có chữ; biểu đồ kiểu trình chiếu nhiều số; chữ nhỏ dài.
Trong bộ dựng: `graphics.js`, `gfx: {type: 'stat', icon}`, `catalog.icons`, `gfx: {type: 'diagram'}`

## 9. Thẻ tiêu đề và thẻ câu hỏi cuối

Thẻ tiêu đề hiện trong khoảng 30–55 s đầu: một câu hỏi "what if" hai dòng in hoa, có chân (serif); dòng hai to hơn, màu vàng có quầng sáng, đặt trên cảnh mờ hoặc nền tím. Thẻ cuối là một câu hỏi ở trên cùng, hai ô lựa chọn có biểu tượng ở giữa, và một hàng 6–12 nhân vật nhỏ toàn thân (dàn diễn viên của tập) đứng dọc mép dưới. Thẻ cuối được giữ lâu.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| lúc thẻ tiêu đề hiện (s) | 47 | 29–54 | motion-depth §4.6 |
| độ dài thẻ cuối (s) | 7 | 4,6–9,9 | motion-depth §4.7 |
| số nhân vật ở thẻ cuối | 8 | 6–12 | visual §9.12 |

Bằng chứng: v06_shots_1.jpg#12, v07_shots_1.jpg#24, v09_shots_1.jpg#31, v10_shots_6.jpg#40, v04_shots_4.jpg#40, v09_shots_5.jpg#18
Nên làm: tiêu đề hai dòng in hoa có chân, dòng hai vàng to; thẻ cuối có câu hỏi, hai ô có biểu tượng (có/không) và hàng nhân vật 3D thật của tập; giữ thẻ cuối 5–10 s.
Không nên làm: chữ mảnh nhỏ; lựa chọn là chấm tròn phẳng; thẻ cuối không có nhân vật; chép câu hỏi hay tiêu đề của kênh mẫu.
Trong bộ dựng: `gfx: {type: 'title'}`, `gfx: {type: 'end-choice', options, cast}`, `figure.js` cho dàn nhân vật

## 10. Cảnh không khí

Phần lớn cảnh ở tông tím hoàng hôn. Rời tông tím là một nhịp kể chuyện ngắn, không phải một kiểu nhìn thứ hai. Báo động phủ đỏ hồng cả khung (hành lang, phòng khi có lệnh khoá cửa). Đêm và căng thẳng ngả xanh tối, có đèn thành đốm. Sau biến cố là trắng tím sáng. Sân cỏ và bàn chơi ngả xanh lá, phòng tập và quán ngả cam. Tường hay trời tím vẫn còn trong khung.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| cảnh tông tím | 67 % | — phần còn lại là nhịp ngắn | visual §1.9 |
| cảnh cam ấm | 12,5 % | 7–18 % (theo phim) | visual §1.9, §10.3 |
| cảnh xanh lá | 4 % | 1–16 % (theo phim) | visual §1.9, §10.3 |
| cảnh trắng tím | 3 % | ≤ 9 % (theo phim) | visual §1.9, §10.3 |

Bằng chứng: v02_shots_1.jpg#21, v02_shots_3.jpg#20, v05_shots_5.jpg#8, v06_shots_4.jpg#13, v07_shots_5.jpg#9, v04_shots_3.jpg#30
Nên làm: đổi tông cả khung cho một nhịp (báo động đỏ hồng, đêm xanh, sau biến cố trắng tím) rồi trở lại tím; giữ một mảng tím trong khung.
Không nên làm: đổi tông kéo dài thành một kiểu nhìn mới; báo động mà không đổi màu cả khung; cảnh đêm đen đặc không có đốm đèn.
Trong bộ dựng: `catalog.moods` (`dusk`, `alarm`, `night`, `lilac`), `scene.mood`, `scene.grade`

## 11. Diễn xuất nhân vật

Cảnh nào cũng có **một việc xảy ra trong cảnh**. Có thể là nét mặt đổi (mí sụp hay mở, cười chuyển sang chữ "o", mày nhíu lại), một động tác tay (đưa, chạm, đẩy, ôm mặt, vẫy), một cái đầu nghiêng hay quay về phía máy, miệng mấp máy khi bong bóng thoại bật lên, hay một đạo cụ tự diễn. Động tác lên nhanh rồi giữ, không lặp vòng. Người trong đám đông đứng yên khi chủ thể diễn. Khi máy đứng, gần như luôn có gì đó động. Cảnh có người mà máy đứng và không có cử động nào rất hiếm.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| thời gian lên của một động tác (s) | 0,417 | 0,25–0,833 | template.json → motion.rise_s |
| phần cảnh có cử động (máy đứng, có người; p25–p75) | — | 0,254–1,0 | template.json → motion.person_still_cam_active |
| cảnh máy đứng có người mà không cử động | 0,108 | — hiếm | template.json → motion.person_still_cam_none |
| thời lượng "người đứng yên" tối đa mỗi phim | 0,055 | 0,003–0,055 | template.json → motion.dead_share_max |

Bằng chứng: v09/strips/S082.jpg#0, v06/strips/S192.jpg#5, v05/strips/S062.jpg#4, v03/strips/S149.jpg#6, v06/strips/S215.jpg#2, v06/strips/S180.jpg#6, v01/strips/S146.jpg#3
Nên làm: mỗi cảnh một việc: đổi nét mặt, một động tác tay, một cái nghiêng đầu hay một đạo cụ tự diễn; động tác lên trong 0,25–0,8 s rồi giữ; miệng mấp máy khi có bong bóng; chớp mắt cho cảnh dài.
Không nên làm: cảnh có người mà máy đứng và không có gì động; cả đám đông cùng diễn; động tác lặp vòng như máy.
Trong bộ dựng: `cast[].act`, `cast[].talk`, `cast[].blink`, `cast[].path`, `catalog.acts`

## 12. Chuyển động máy

Máy **đẩy chậm vào** là mặc định. Khoảng một nửa số cận và trung cảnh có máy đẩy vào, tốc độ khoảng 1–5 %/s. Máy đứng thật (không dời, không phóng) chỉ khoảng một phần ba thời lượng. Máy trôi ngang hay dọc rất hiếm. Máy bám theo khi nhân vật chạy hoặc đi. Những cú máy lớn để dành cho cảnh đinh: lia lên mặt nhà, tiến dài theo hành lang, bám theo máy bay. Đồ hoạ trọn khung thường đứng yên.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| thời lượng máy đứng thật (theo phim) | 0,364 | 0,243–0,836 | template.json → motion.still_ratio |
| cận có máy đẩy vào | 0,589 | 0,39–0,62 (theo cỡ) | template.json → motion.cam_by_scale.cu.push |
| trung cảnh có máy đẩy vào | 0,495 | 0,39–0,62 (theo cỡ) | template.json → motion.cam_by_scale.med.push |
| tốc độ đẩy ở cận (%/s, p25–p75) | — | 0,955–4,271 | template.json → motion.cam_by_scale.cu.zoom_pct_s |
| tốc độ máy dời ở trung cảnh (px/s ở 1280, p25–p75) | — | 13,86–46,358 | template.json → motion.cam_by_scale.med.drift_px_s |
| motion720 p50 (theo phim) | — | 0,008–0,176 | template.json → motion.motion720_p50 |

Bằng chứng: v01/strips/S010.jpg#7, v10/strips/S073.jpg#0, v02/strips/S160.jpg#0, v06/strips/S190.jpg#4, v04/strips/S065.jpg#4, v01_shots_1.jpg#3
Nên làm: đẩy chậm vào ở khoảng một nửa số cận và trung cảnh, có lúc bắt đầu và dừng mềm; bám theo khi nhân vật chạy; giữ cú máy lớn cho cảnh đinh; đồ hoạ trọn khung để đứng.
Không nên làm: máy đứng chết ở mọi cảnh; lia nhanh, rung tay; trôi ngang liên tục.
Trong bộ dựng: `move: 'auto' | {type, speed}`, `catalog.moves`, `camera.js → place`

## 13. Chuyển cảnh

Gần như toàn là cắt thẳng. Mờ dần ra đen chỉ dùng một hai lần mỗi phim để khép một hồi. Nháy đen ngắn là một nhịp trong cận đang giữ. Đổi trạng thái hay trang phục dùng một vệt sáng 0,15 s ngay trong cảnh, không dùng ở chỗ cắt. Không mờ chồng, không trượt.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| chỗ cắt là cắt thẳng | 0,9904 | — gần như tất cả | template.json → transitions.cut |
| mờ dần mỗi phim | 0,3 | 0–2 | template.json → transitions.fade_per_film |
| độ dài nháy đen (s) | — | 0,117–0,162 | template.json → transitions.dip_s |
| vệt sáng đổi trạng thái (s) | 0,15 | 0,13–0,17 | motion-depth §2.3 |

Bằng chứng: v01/strips/S081.jpg#6, v04/strips/S054.jpg#6, v07/strips/S215.jpg#5, v02_shots_3.jpg#20
Nên làm: cắt thẳng; vệt sáng 0,15 s để nhân vật đổi trạng thái trong cảnh; nháy đen 0,12 s làm nhịp; mờ dần đen tối đa 2 lần để khép hồi.
Không nên làm: mờ chồng giữa hai cảnh; vật che trượt; hiệu ứng chuyển cảnh trang trí.
Trong bộ dựng: `trans: 'cut' | 'dip' | 'fade'`, `act: 'swap'` (vệt sáng trong cảnh), `stage.js`

## 14. Âm thanh

Nhạc nền chạy liền suốt phim, kể cả dưới lời. Trong các khoảng nghỉ của lời, nhạc chỉ thấp hơn giọng vài dB, nên khoảng nghỉ không bao giờ trống. Tempo đều, vào khoảng 115–120 BPM (độ tin cậy thấp). Tiếng động dày: điểm bật âm ngoài lời khoảng 18–43 lần mỗi phút (mức trần, có lẫn phách nhạc). Bản trộn nén chặt ở −14 LUFS.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| cửa sổ 5 s có nhạc | 0,975 | — gần như liền | template.json → sound.music_share |
| nhạc trong khoảng nghỉ so với giọng (dB, p25–p75) | — | -8,5–-3,3 | template.json → sound.music_under_voice_db |
| điểm bật âm ngoài lời mỗi phút (theo phim, mức trần) | — | 18,19–42,96 | template.json → sound.sfx_per_min |
| tempo (BPM, độ tin cậy thấp) | — | 114–120 | template.json → sound.tempo |
| độ lớn (LUFS) | −14 | −14,4 – −14,0 | sound-script §6.1 |

Bằng chứng: v01/evidence/sfx-a.jpg, v04/evidence/sfx-b.jpg, v06/evidence/sfx-c.jpg
Nên làm: nhạc nền liền suốt phim, giảm vừa đủ khi có lời; tiếng động cho việc trong cảnh (đạo cụ, bước chân, số đếm đang chạy); một tiếng nhẹ khi thẻ số liệu hoặc thẻ cuối hiện, bong bóng thoại và số đếm đứng yên thì im lặng (luật của xưởng, người dùng chọn 2026-11-18: chưa có bằng chứng kênh mẫu phát tiếng mỗi khi đồ hoạ hiện); −14 LUFS, dải âm lượng hẹp.
Không nên làm: khoảng lặng trống; nhạc tắt giữa phim; tiếng bụp mỗi lần một bong bóng hay con số hiện ra; dùng nhạc của kênh mẫu hay nhạc bên ngoài.
Trong bộ dựng: `kit/sound/score.py`, `kit/sound/sfx.py`, `kit/sound/mix.py`, `events.json`

## 15. Nhịp đọc lời

Giọng đọc nhanh và liền, khoảng 140–200 từ mỗi phút, không chậm lại ở cao trào. Nghỉ giữa các từ trong câu ngắn, nghỉ cuối câu dài hơn một chút, nghỉ giữa đoạn dưới 0,75 s. Trước một con số có một khoảng nghỉ dài hơn nghỉ cuối câu, để con số đến như một nhịp nhấn. (Mốc từ lấy từ máy nhận dạng giọng nên các khoảng nghỉ đo được dài hơn thật. `kit/sound/timing.py → fit` co tất cả cùng một hệ số, giữ thứ tự trước số > giữa đoạn > cuối câu > trong câu, cho tới khi khoảng lặng của giọng ≤ 20 % phim (luật của xưởng, specs/020); phim nhiều dòng ngắn co tới ≈ 0,35.)

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| từ mỗi phút (cửa sổ 10 s, p10–p90) | 168,0 | 138,0–198,0 | template.json → voice.wpm |
| nghỉ trong câu (s) | — | 0,28–0,44 | template.json → voice.pause_in |
| nghỉ cuối câu (s) | — | 0,42–0,54 | template.json → voice.pause_sent |
| nghỉ giữa đoạn (s) | — | 0,64–0,74 | template.json → voice.pause_para |
| nghỉ trước con số (s) | — | 0,46–0,64 | template.json → voice.pre_number |

Bằng chứng: v06/evidence/number-a.jpg, v09/evidence/number-b.jpg, v09/evidence/number-c.jpg
Nên làm: giữ giọng của kênh; xếp dòng theo các khoảng nghỉ trên; để một khoảng nghỉ dài hơn trước mỗi con số; câu ngắn.
Không nên làm: nghỉ giữa đoạn trên 1 s; chậm lại ở cao trào; bắt chước giọng của kênh mẫu.
Trong bộ dựng: `kit/sound/timing.py → schedule`, `voice make` (`say` cho chữ đọc sai)

## Công thức nhịp

Đo trên 9 phim có `beats.json` (v02 không xếp theo thứ tự chuẩn nên bỏ ra). Độ dài cảnh là p25–p75. "Diễn xuất" là phần cảnh máy đứng có người mà có cử động.

### hook

| Mục | Giá trị |
|---|---|
| độ dài cảnh (s) | 1,43–2,85 |
| chuỗi cỡ cảnh hay gặp | med → med → med; wide → cu → cu; med → med → cu |
| máy động | 69 % số cảnh |
| diễn xuất | 95 % cảnh máy đứng có người |
| đồ hoạ | 4 % cảnh là đồ hoạ trọn khung; thẻ tiêu đề câu hỏi ở 30–55 s; ít đồ hoạ trọn khung |
| chuyển cảnh | cắt thẳng |
| tiếng động | 29,51 điểm bật mỗi phút (mức trần) |
| nhạc | liền; trong khoảng nghỉ thấp hơn giọng 5,3 dB |
| từ mỗi phút | 162 |

### explain

| Mục | Giá trị |
|---|---|
| độ dài cảnh (s) | 2,53–5,81 |
| chuỗi cỡ cảnh hay gặp | wide → insert → wide; wide → wide → insert; insert → wide → cu |
| máy động | 35 % số cảnh |
| diễn xuất | 97 % cảnh máy đứng có người |
| đồ hoạ | 28 % cảnh là đồ hoạ trọn khung; nhiều thẻ số liệu trọn khung xen cảnh rộng (cảnh rộng → thẻ → cảnh rộng) |
| chuyển cảnh | cắt thẳng |
| tiếng động | 30,08 điểm bật mỗi phút (mức trần) |
| nhạc | liền; trong khoảng nghỉ thấp hơn giọng 6,4 dB |
| từ mỗi phút | 168 |

### benefit

| Mục | Giá trị |
|---|---|
| độ dài cảnh (s) | 1,46–3,23 |
| chuỗi cỡ cảnh hay gặp | med → med → med; wide → med → med; wide → wide → wide |
| máy động | 61 % số cảnh |
| diễn xuất | 92 % cảnh máy đứng có người |
| đồ hoạ | 7 % cảnh là đồ hoạ trọn khung; số đếm và nhãn trên cảnh; thẻ số liệu rải rác |
| chuyển cảnh | cắt thẳng |
| tiếng động | 31,28 điểm bật mỗi phút (mức trần) |
| nhạc | liền; trong khoảng nghỉ thấp hơn giọng 3,7 dB |
| từ mỗi phút | 168 |

### scale

| Mục | Giá trị |
|---|---|
| độ dài cảnh (s) | 1,67–3,85 |
| chuỗi cỡ cảnh hay gặp | med → med → med; huge → huge → med; huge → med → med |
| máy động | 58 % số cảnh |
| diễn xuất | 92 % cảnh máy đứng có người |
| đồ hoạ | 10 % cảnh là đồ hoạ trọn khung; số lớn trên cảnh rất rộng, thẻ số liệu |
| chuyển cảnh | cắt thẳng |
| tiếng động | 29,52 điểm bật mỗi phút (mức trần) |
| nhạc | liền; trong khoảng nghỉ thấp hơn giọng 4,8 dB |
| từ mỗi phút | 168 |

### cost

| Mục | Giá trị |
|---|---|
| độ dài cảnh (s) | 1,62–3,88 |
| chuỗi cỡ cảnh hay gặp | med → wide → med; med → med → wide; wide → cu → med |
| máy động | 60 % số cảnh |
| diễn xuất | 80 % cảnh máy đứng có người |
| đồ hoạ | 3 % cảnh là đồ hoạ trọn khung; ít đồ hoạ |
| chuyển cảnh | cắt thẳng |
| tiếng động | 21,4 điểm bật mỗi phút (mức trần) |
| nhạc | liền; trong khoảng nghỉ thấp hơn giọng 11,6 dB |
| từ mỗi phút | 168 |

### crisis

| Mục | Giá trị |
|---|---|
| độ dài cảnh (s) | 1,71–4,3 |
| chuỗi cỡ cảnh hay gặp | huge → huge → huge; huge → cu → huge; huge → huge → cu |
| máy động | 60 % số cảnh |
| diễn xuất | 90 % cảnh máy đứng có người |
| đồ hoạ | 9 % cảnh là đồ hoạ trọn khung; đồng hồ đếm ngược, thẻ số liệu y tế hay vật lý |
| chuyển cảnh | cắt thẳng |
| tiếng động | 25,02 điểm bật mỗi phút (mức trần) |
| nhạc | liền; trong khoảng nghỉ thấp hơn giọng 6,2 dB |
| từ mỗi phút | 162 |

### ending

| Mục | Giá trị |
|---|---|
| độ dài cảnh (s) | 1,5–4,23 |
| chuỗi cỡ cảnh hay gặp | med → cu → cu; med → wide → cu; wide → cu → cu |
| máy động | 62 % số cảnh |
| diễn xuất | 86 % cảnh máy đứng có người |
| đồ hoạ | 5 % cảnh là đồ hoạ trọn khung; ít đồ hoạ; số đếm lần cuối |
| chuyển cảnh | cắt thẳng |
| tiếng động | 19,18 điểm bật mỗi phút (mức trần) |
| nhạc | liền; trong khoảng nghỉ thấp hơn giọng 6,5 dB |
| từ mỗi phút | 180 |

### sting

| Mục | Giá trị |
|---|---|
| độ dài cảnh (s) | 1,54–3,5 |
| chuỗi cỡ cảnh hay gặp | med → med → med; med → cu → med; cu → med → med |
| máy động | 67 % số cảnh |
| diễn xuất | 90 % cảnh máy đứng có người |
| đồ hoạ | 3 % cảnh là đồ hoạ trọn khung; ít đồ hoạ |
| chuyển cảnh | cắt thẳng |
| tiếng động | 23,3 điểm bật mỗi phút (mức trần) |
| nhạc | liền; trong khoảng nghỉ thấp hơn giọng 8,6 dB |
| từ mỗi phút | 174 |

### end-card

| Mục | Giá trị |
|---|---|
| độ dài cảnh (s) | 8,53–9,7 |
| chuỗi cỡ cảnh hay gặp | huge → insert → huge; insert → huge → insert; huge → insert → insert |
| máy động | 11 % số cảnh |
| diễn xuất | 100 % cảnh máy đứng có người |
| đồ hoạ | 67 % cảnh là đồ hoạ trọn khung; thẻ câu hỏi cuối có hai lựa chọn và hàng nhân vật |
| chuyển cảnh | nháy đen hoặc mờ dần vào thẻ cuối |
| tiếng động | 54,43 điểm bật mỗi phút (mức trần) |
| nhạc | liền; trong khoảng nghỉ thấp hơn giọng 6,9 dB |
| từ mỗi phút | 126 |
