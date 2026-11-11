# Contract: các tệp của gói đăng

Mọi tệp nằm trong `films/<tên>/publish/`:
- Agent chỉ viết `pack.json`.
- Lệnh `publish` viết mọi tệp còn lại, và mỗi lần chạy thì xoá các tệp cũ của nó trước, trừ `pack.json`.

## pack.json (agent viết)

```json
{
  "language": "en",
  "titles": [
    {"angle": "curiosity", "text": "Why Honey in a Pharaoh's Tomb Was Still Edible",
     "thumb": {"t": 12.5, "text": "3,000 years old", "position": "bottom"}},
    {"angle": "number", "text": "3,000 Years and Not Spoiled: The Chemistry of Honey",
     "thumb": {"t": 24.0, "text": "Bees did this", "color": "#ffd23f", "plate": "#1a1a1a", "plate_opacity": 0.7}},
    {"angle": "question", "text": "Can Honey Really Last Forever?",
     "thumb": {"t": 38.2, "text": "Forever food?", "position": "top"}}
  ],
  "hook": ["Archaeologists found honey in an Egyptian tomb.", "It was still good to eat."],
  "summary": "A 50-second look at why honey resists bacteria: low water, high acid, and an enzyme bees add.",
  "chapters": [{"from": "P01", "title": "The tomb"}, {"from": "P03", "title": "Too dry for germs"},
               {"from": "P05", "title": "The bees' secret"}],
  "hashtags": ["#honey", "#science", "#food"]
}
```

Luật của từng trường xem ở data-model.md. Số trong ví dụ trên phải có trong `SCRIPT.md` hoặc `SOURCES.md`.

## titles.md

```markdown
# Titles

1. **Curiosity:** Why Honey in a Pharaoh's Tomb Was Still Edible
   Thumbnail: thumbnail-1.png ("3,000 years old")
2. **Number or benefit:** …
3. **Question:** …
```

## description.md

Tệp là chữ thuần, dán thẳng vào YouTube Studio được. Thứ tự các phần (FR-004):

```text
Archaeologists found honey in an Egyptian tomb.
It was still good to eat.

A 50-second look at why honey resists bacteria: low water, high acid, and an enzyme bees add.

0:00 The tomb
0:14 Too dry for germs
0:31 The bees' secret

Sources:
- Smithsonian Magazine, 2013: https://…
- …

#honey #science #food
```

- Không có chương: bỏ cả khối chương.
- `SOURCES.md` là `no factual claims`, hoặc chỉ có dòng `fiction`/`provided:`: bỏ khối `Sources:`.
- Mỗi nguồn chỉ ghi một lần, dù được dẫn ở nhiều đoạn.

## subtitles.srt

Đây là SRT chuẩn, mã hoá UTF-8 và xuống dòng bằng `\n`. Chữ lấy từ kịch bản đã đạt, giữ nguyên dấu câu (R5).

## thumbs.json

`[{"file": "thumbnail-1.png", "t": 12.5, "w": 1280, "h": 720, "bytes": 812345, "text": "…", "font": "Inter", "text_height_ratio": 0.11, "contrast": 7.2, "bg_luma": [0.08, 0.61], "missing_glyphs": []}, …]`

## PUBLISH.md

```markdown
# Publish: <tiêu đề làm việc của SCRIPT.md, hoặc tên phim>

Video: ../<tên>.mp4 · Subtitles: subtitles.srt (English)

## Pick one pair
| # | Angle | Title | Thumbnail | Text on it |
|---|---|---|---|---|
| 1 | Curiosity | … | thumbnail-1.png | … |

## Description (copy all)
<nội dung description.md>

## Missing
- Subtitles and chapters: no narration.json (made before 010).
```

- Mục `## Missing` chỉ có khi thiếu phần nào.
- Gói trượt máy kiểm thì có thêm mục `## Check problems`, liệt kê lỗi.

## checks.json

Thêm khoá `publish` (data-model.md). `report.empty()` có `"publish": None`; `report.load()` giữ nguyên khoá này khi các lệnh của 010 ghi tệp.
