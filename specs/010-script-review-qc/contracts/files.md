# Contract: các tệp trong thư mục phim

Mọi tệp nằm trong `films/<name>/`. Agent viết `BRIEF.md` (chỉ local), `SCRIPT.md`, `SOURCES.md`, `narration.json`. Công cụ của xưởng viết `checks.json`, `CHECKS.md` và thư mục `.check/`; agent không sửa chúng.

## BRIEF.md (agent viết, chỉ local)

Tóm tắt yêu cầu của phim sau bước Brief của thư viện: chủ đề, phong cách, thời lượng, ngôn ngữ, những gì người dùng bắt buộc có hoặc không có. Tối đa 2000 ký tự, chữ thường. Biên tập đọc tệp này như "yêu cầu của phim" (FR-007). Online thì biên tập đọc `/work/.input.json` thay cho tệp này.

## SCRIPT.md (agent viết, FR-001)

```markdown
Title: The Baker Who Wakes the Street
Target: 45s
Language: en
Speed: 150            # tuỳ chọn: từ/phút (en, vi) hoặc ký tự/giây (zh, ja, ko)

[P01] Hanoi sleeps until four. One man does not.
[P02] ...
```

- Ba dòng đầu `Title`, `Target` (giây, có hậu tố `s`), `Language` (mã `en`, `vi`, `zh`…) là bắt buộc.
- Mỗi đoạn bắt đầu bằng `[Pnn]` ở đầu dòng, `nn` tăng dần từ 01, không trùng. Một đoạn có thể nhiều dòng.
- Chỉ phần sau `[Pnn]` là lời đọc. Dòng bắt đầu bằng `>` là ghi chú cho người làm, máy chấm bỏ qua.

## SOURCES.md (agent viết, FR-002)

```markdown
- [P01] "Hanoi sleeps until four": Hanoi Department of Transport, 2024, https://…
- [P03] "1.2 million motorbikes": …, 2023, https://…
```

- Mỗi dòng: `- [Pnn] "<trích>": <tên nguồn>, <năm>, <đường dẫn>`.
- Tài liệu do người giao phim đưa: thay đường dẫn bằng `provided:<tên tệp>`.
- Chi tiết bịa trong truyện hư cấu (spec FR-004 "truyện hư cấu"): `- [Pnn] "<trích>": fiction`. Biên tập vẫn đọc dòng này và ghi P1 nếu đó là sự thật bị gắn nhãn sai.
- Không có số liệu: một dòng duy nhất `no factual claims`.

## narration.json (agent viết, R5)

```json
{
  "words_file": "voices/words.json",
  "durations_file": "voices/dur.json",
  "lines": [
    {"id": "l01", "para": "P01", "at": 0.60},
    {"id": "l02", "para": "P01", "at": 3.10}
  ],
  "cuts": [0.0, 4.2, 9.8]
}
```

- `words_file`: tệp `words.json` của `asr_check.py`, gồm `{ "<id>": [[từ, bắt đầu, kết thúc], …] }`, mốc tính từ đầu dòng.
- `at`: giây bắt đầu của dòng trong phim cuối.
- `cuts` (tuỳ chọn): mốc chuyển cảnh, tính bằng giây. Thiếu thì `qc` tìm từ hình.
- Đường dẫn tương đối với thư mục phim.

## .check/ (công cụ viết)

- `opened.json`: `[{"url", "final_url", "status", "at"}]`, mỗi lần `web fetch`.
- `script-r<n>.md`: bản kịch bản lúc biên tập lượt n.
- `review-r<n>.json`: trả lời của biên tập lượt n (đúng lược đồ ở cli.md).

## checks.json (công cụ viết, FR-015)

```json
{
  "narration": true,
  "script": {
    "verdict": "pass | failed | pending | skipped",
    "skip_reason": "no narration",
    "machine": [{"round": 0, "score": 8.5, "hard": {"format": true, "sources": true, "length": true, "unchanged": true}, "issues": [{"para": "P02", "sentence": 1, "rule": "long_sentence", "detail": "31 words"}]}],
    "editor":  [{"round": 1, "model": "opus", "score": 7.5, "p1": 1, "p2": 2, "p3": 0, "issues": [{"level": "P1", "para": "P03", "reason": "…"}]}],
    "fix_rounds": 1
  },
  "film": {
    "pass": true,
    "measures": {
      "silence_ratio": 0.14, "long_pauses_bad": [], "cuts_bad": [], "key_shots_bad": [],
      "tail_s": 0.9, "stills_bad": [], "missing_glyphs": [], "texts_checked": true
    },
    "problems": []
  }
}
```

`CHECKS.md` là bản người đọc của cùng nội dung: bảng điểm từng lượt, danh sách lỗi, bảng số đo và ngưỡng, kết luận.
