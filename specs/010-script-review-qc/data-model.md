# Data model: Kịch bản được chấm và QC video tự động

Phần lớn dữ liệu nằm trong tệp của thư mục phim ([contracts/files.md](contracts/files.md)). Cơ sở dữ liệu online chỉ thêm một cài đặt và mở rộng trường `qa` của Job.

## Script (tệp `SCRIPT.md`)
| Trường | Luật |
|---|---|
| title | bắt buộc, ≤ 100 ký tự |
| target_s | bắt buộc, số nguyên 5–900 |
| language | bắt buộc, mã ngôn ngữ (`en`, `vi`, `zh`, `ja`, `ko`, …) |
| speed | tuỳ chọn; mặc định theo ngôn ngữ (R2) |
| paragraphs | ≥ 1; id `Pnn` tăng dần từ `P01`, không trùng; nội dung không rỗng |

## Source (dòng trong `SOURCES.md`)
| Trường | Luật |
|---|---|
| para | id có trong Script |
| quote | chuỗi có trong đoạn đó (so không phân biệt hoa thường) |
| name, year | bắt buộc; năm 4 chữ số |
| url | `http(s)://…` đã có trong `opened.json` với mã 2xx, hoặc `provided:<tệp>` |

Hoặc đúng một dòng `no factual claims`.

## Script review (một lượt chấm, trong `checks.json`)
| Trường | Luật |
|---|---|
| who | `machine` hoặc `editor` |
| round | machine: lượt chạy; editor: 1–3 (1 + tối đa 2 vòng sửa), cộng các lượt do người giao phim yêu cầu (FR-019) |
| model | chỉ với editor: model thật đã dùng |
| score | 0–10, một chữ số thập phân |
| hard | machine: `format`, `sources`, `length`, `unchanged` (true/false) |
| issues | machine: `{para, sentence, rule, detail}`; editor: `{level P1/P2/P3, para, reason}` |

**Trạng thái của kịch bản** (`script.verdict`):

```
pending ──(editor ≥ 8, P1 = 0)──► pass
pending ──(hết 2 vòng sửa)──────► failed      (online: việc lỗi do xưởng, trả lượt)
(không có lời đọc) ─────────────► skipped
pass ──(người giao phim yêu cầu sửa, FR-019)──► pending
```

## QC result (`checks.json.film`, chép vào `job.qa.film`)
| Trường | Luật |
|---|---|
| silence_ratio | 0–1; đạt khi ≤ 0,20 |
| long_pauses_bad | danh sách `{at, length}` |
| cuts_bad | danh sách `{at, sentence_end}` |
| key_shots_bad | danh sách `{para, shot_length}` |
| tail_s | giây; đạt khi ≤ 1,5 |
| stills_bad | danh sách `{from, to}` |
| missing_glyphs | danh sách `{char, codepoint, text}` |
| texts_checked | false khi phim không có `window.TEXTS` |
| problems | các câu lỗi đưa vào `qa.problems` của 007 |

## Job (online, sửa 007)
- `qa.script`: `{verdict, machine_score, editor_score, fix_rounds, p1, p2, p3, model}`.
- `qa.film`: QC result ở trên.
- Danh sách bước thêm `Script` giữa `Treatment` và `Look`.

## Settings (online, sửa 008)
- Thêm `editor_model`: một trong `inherit`, `opus`, `sonnet`, `haiku`; mặc định `inherit`. Chỉ admin đổi.

## Config (local)
- `.studio/config.json`: `{"editor_model": "inherit"}`; tệp không vào git (`.studio/` đã bị bỏ qua).
