# Contract: các tệp của kênh và bài học

Khuôn dạng các trường xem ở data-model.md. Mọi tệp ghi bằng UTF-8.
- Tệp JSON do lệnh `channel` và `lesson` (hoặc API online) ghi. Người dùng có thể sửa tay; `channel show` và `lesson list` kiểm lại.
- Tệp Markdown luôn được viết lại từ JSON. Đừng sửa tay, vì lần ghi sau sẽ xoá thay đổi.

## `channels/<slug>/CHANNEL.md`

```markdown
# Kênh Khoa học vui (`khoa-hoc-vui`)

Cập nhật: 2026-11-11

- Ngách: khoa học đời thường · Khán giả: 18–35, thích giải thích ngắn
- Ngôn ngữ: vi · Độ dài: 45 s · Phong cách: dark-keynote · Giọng: af_bella × 1.0
- Hashtag luôn dùng: #khoahoc · Từ không dùng: sốc, kinh hoàng
- Tiêu đề (tối đa 70): <title_rules>
- Thumbnail: <thumbnail_rules>

## Quyết định
- 2026-11-11: Không dùng nhạc có lời.
```

## `channels/<slug>/LESSONS.md` và `channels/LESSONS.md`

```markdown
# Bài học: khoa-hoc-vui

| # | Ngày | Trạng thái | Lỗi | Vì sao lọt | Cách chặn | Luật máy |
|---|---|---|---|---|---|---|
| 3 | 2026-11-11 | active | Tiêu đề kiểu câu view | Không có luật | Không dùng "you won't believe" | `phrase:you won't believe` |
```

## `channels/README.md` (local, vào git)

Danh mục các kênh, gồm mã, tên, ngôn ngữ, phong cách, số bài học. Bảng được viết lại mỗi khi một kênh thay đổi.

## Bản chụp trong thư mục phim

- `films/<phim>/channel.json`: data-model.md.
- `films/<phim>/CHANNEL_BRIEF.md`: phần agent và biên tập đọc. Gồm `# Channel: <tên>`, các dòng hồ sơ, `## Decisions`, `## Lessons` ("#n <what> → <stop>"). Tối đa 6000 ký tự.

## `films/<phim>/LESSON_DRAFT.json` (agent viết, chỉ ở việc sửa phim online có `lesson: true`)

```json
{"what": "The ending felt rushed", "why": "No rule checks the last shot", "stop": "Hold the last shot 2 s longer",
 "rule": null}
```

Worker đọc tệp này sau khi việc xong và lưu thành bài học `draft` của kênh. Tệp sai khuôn dạng thì bị bỏ qua, và log việc ghi một dòng.
