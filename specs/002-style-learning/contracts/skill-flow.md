# Contract: skill `style-learn`

Kích hoạt khi người dùng muốn học phong cách của một kênh, một danh sách video, hoặc file video có sẵn. Mọi câu nói với người dùng bằng ngôn ngữ của họ; mọi file phong cách bằng tiếng Anh (FR-016a).

| # | Bước | Ai làm | Dừng chờ người dùng? |
|---|---|---|---|
| 0 | Hỏi một lần nếu thiếu: nguồn, số video, tên bộ, tên cấm thêm | Claude | Chỉ khi thiếu thông tin |
| 1 | `deps learn` (lần đầu), `fetch`, `measure`, `transcribe` (nếu có), `summary` | Claude chạy công cụ | Không |
| 2 | Báo cáo nhanh hồ sơ đo; cảnh báo nếu < 5 video, bộ không đồng nhất, hay nhiều định dạng | Claude | Không (người dùng có thể dừng) |
| 3 | 3 agent song song: `visual`, `motion-depth`, `sound-script` → `analysis/*.md` | Agent | Không |
| 4 | Kiểm tra chéo từng kết luận với số đo và bảng ảnh → `analysis/corrections.md` | Claude | Không |
| 5 | Chọn `based_on`; viết `style/STYLE.md` (11 mục), `style.json`, `EVIDENCE.md`; chạy `check-names` | Claude | Không |
| 6 | **Duyệt 1**: tóm tắt tiếng Việt (template `review-vi.md`): bản chất, 10 luật quan trọng nhất kèm số, các kết luận đã sửa | Người dùng | **Có** |
| 7 | Chọn khung gốc tiêu biểu; viết trang `proof/index.html`; chụp bằng `still.mjs`; `compare`; tối đa 2 vòng sửa | Claude | Không |
| 8 | **Duyệt 2**: ảnh ghép, bảng chỉ số, chỉ số nào chưa đạt và vì sao | Người dùng | **Có** |
| 9 | `save` | Claude | Không |
| 10 | Hỏi giữ hay xoá video tham chiếu (mặc định xoá) → `clean` | Người dùng trả lời | Câu hỏi, không phải duyệt |

Quy tắc:
- Không đọc phong cách thư viện nào trước bước 5. Ở bước 5 chỉ đọc `STYLE.md` của phong cách `based_on` để lấy kỹ thuật, không lấy luật.
- Mọi luật trong `STYLE.md` có `(evidence: …)`.
- Không chép câu thoại, tên kênh, tên người, nhân vật, tiêu đề.
- Môi trường không có `node`/`deps` để chụp khung: dừng ở bước 7, báo rõ, giữ bản nháp.
