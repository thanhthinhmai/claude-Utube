# Contract: `TEMPLATE.md` và nhãn luật của `STYLE.md`

`learn template-check <slug>` kiểm đúng các điều dưới đây.

## `TEMPLATE.md`

```markdown
# Template: <Tên phong cách>

Bộ tham chiếu: <set> · <n> video · học ngày <ngày> · luật hình theo <n> phim 3D, nhịp và âm thanh theo <n> phim

## 1. Khuôn mặt và biểu cảm
<mô tả bằng lời của xưởng, 2–6 câu>

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| … | … | p25–p75 | craft-summary.json → … |

Bằng chứng: v01_shots_3.jpg#S087, v04/strips/S112.jpg#3, v07/evidence/face-close.jpg
Nên làm: …
Không nên làm: …
Trong bộ dựng: `figure.face`, `faces: dot|half|…`, `blink`
```

### 15 mục bắt buộc

Mỗi mục đúng tên và đúng thứ tự:

1. Khuôn mặt và biểu cảm
2. Thân và trang phục
3. Bố cục theo cỡ cảnh
4. Độ sâu theo cỡ cảnh
5. Ánh sáng
6. Bối cảnh và đạo cụ kể chuyện
7. Đám đông
8. Thẻ số liệu
9. Thẻ tiêu đề và thẻ câu hỏi cuối
10. Cảnh không khí
11. Diễn xuất nhân vật
12. Chuyển động máy
13. Chuyển cảnh
14. Âm thanh
15. Nhịp đọc lời

### Mỗi mục phải có

- Một đoạn mô tả không rỗng.
- Bảng số đo có ≥ 1 dòng; cột "Khoảng" không rỗng.
- Dòng `Bằng chứng:`. Mỗi bằng chứng có một trong ba dạng: `<bảng>.jpg#Sxxx`, `vNN/strips/Sxxx.jpg#k`, `vNN/evidence/<tên>.jpg`. Cần ≥ 3 bằng chứng từ ≥ 2 video khác nhau, trừ khi có dòng `Ít bằng chứng: <n> khung`. Mọi tệp được dẫn phải có trong `references/<set>/profile/`.
- Dòng `Nên làm:` và dòng `Không nên làm:`.
- Dòng `Trong bộ dựng:` nêu tên trong `kit/catalog.json` hoặc tên module, hàm của bộ dựng.

### Công thức nhịp

Mục `## Công thức nhịp` có 9 mục con `### <nhịp>`, theo thứ tự hook, explain, benefit, scale, cost, crisis, ending, sting, end-card. Mỗi nhịp có bảng các dòng:
- độ dài cảnh (p25–p75);
- chuỗi cỡ cảnh hay gặp;
- tỉ lệ máy động;
- diễn xuất;
- đồ hoạ;
- chuyển cảnh;
- tiếng động mỗi phút;
- nhạc (có hay không, tempo, mức so với giọng);
- từ mỗi phút.

## `template.json`

Có các khoá như data-model.md. Mỗi khoá lá chứa số có một dòng tương ứng trong `source`, hoặc là khoá gốc của `summary.json`. `template-check` so mỗi số trong bảng của `TEMPLATE.md` có `Nguồn` trỏ tới `template.json` hay `craft-summary.json` với giá trị trong tệp (lệch ≤ 0,01 sau khi làm tròn).

## `STYLE.md`

Ở mục 1–11, mỗi dòng bảng (trừ dòng tiêu đề và dòng `|---|`) và mỗi gạch đầu dòng chứa luật mang một trong hai nhãn:
- `[bằng chứng: …]`: ít nhất một trích dẫn dạng bảng#ô, `tệp → khoá`, hoặc `<báo cáo> §n.m`;
- `[xưởng]`.

Luật phụ đề in trên hình mang `[xưởng]`. Thiếu nhãn thì `template-check` báo số dòng.
