# Contract: luật và kết quả kiểm (020)

## Bảng luật

| Tầng | Luật | Mức | Ngưỡng (mặc định) | Ngoại lệ được? |
|---|---|---|---|---|
| voice | `pause_in_line` | block | ≥ 0,8 s giữa hai từ của một dòng | không (làm lại dòng) |
| voice | `asr_mismatch` | block | độ giống < 0,92 (như asr_check) | không |
| voice | `tail_mismatch` | block | \|từ cuối − dur\| > 0,5 s | không |
| plan | `cut_in_sentence` | block | cắt nằm trong câu (± 0,05 s) | không |
| plan | `cut_too_soon` | block | cắt < min(0,4 s, khoảng tới câu sau) sau khi câu dứt | không |
| plan | `key_shot_short` | block | cảnh chứa từ cuối của đoạn < 2,5 s | không |
| plan | `silence` | block | lặng > 20% | không |
| plan | `pause_in_para` | block | nghỉ ≥ 0,8 s trong một đoạn | không |
| plan | `tail` | block | > 1,5 s sau từ cuối | không |
| plan | `shot_short` | block | cảnh < 1,1 s | không |
| plan | `shot_long` | block | cảnh > `shot_max` (6 s) | có |
| plan | `cue_short` | block | phụ đề < max(1,8 s, thời gian nói + 0,6 s) | không |
| plan | `card_read` | block | thẻ chữ hiện ngắn hơn luật đọc của thư viện | không |
| shots | `flat` | block | màu nhiều nhất > 60% hoặc độ lệch độ sáng < 0,04 (không tính chữ, letterbox) | có |
| shots | `dark` | block | độ sáng p50 < 0,04 | có |
| shots | `blown` | block | > 25% điểm có độ sáng > 0,98 | có |
| shots | `missing_glyph` | block | ký tự không có phông | không |
| shots | `text_over_subtitle` | block | chữ cắt vùng phụ đề lúc có phụ đề | có |
| shots | `style_luma` | warn | độ sáng p50 của phim ngoài khoảng của phong cách | lý do chung (`accept-style`) |
| shots | `style_saturation` | warn | bão hoà p50 ngoài khoảng | như trên |
| shots | `style_cuts_per_min` | warn | số cắt mỗi phút ngoài khoảng (bỏ qua khi phim < 30 s) | như trên |
| render | `black_frames` | block | khung đen ≥ 0,25 s | không |
| render | `still` | block | đứng yên > `still_max` (6 s) | có |
| final | các luật nhịp của `plan` | block | cùng code (`rhythm.py`) | như plan |
| final | `loudness_range` | warn | dải âm lượng ngoài khoảng của phong cách | lý do chung |
| final | `av_sync` | block | \|tiếng − hình\| > 0,1 s | không |
| final | các luật hiện có của 010 (stills, glyphs, channel voice, voice ↔ script) | như 010 | như 010 | như 010 |

`pause_in_line` (tầng 0) và `pause_in_para` (tầng 1) có thể báo cùng một khoảng nghỉ. Tầng 1 là lưới thứ hai cho trường hợp giọng đổi sau tầng 0.

`cue_short`, `shot_short`, `shot_long` là luật mới, nên `qc` sau ghép tiếng cũng áp dụng chúng (FR-010). Phim cũ đã giao trước 020 có thể bị báo thêm các lỗi này khi chạy `qc` lại.

## `checks.json`
Thêm khoá `tiers`; các khoá cũ (`narration`, `script`, `film`, `publish`) giữ nguyên:

```json
{"tiers": {
  "voice":  {"pass": true,  "fingerprint": "…", "at": "…", "issues": [], "measures": {}, "skipped": [], "seconds": 4.1},
  "plan":   {"pass": false, "fingerprint": "…", "issues": [{"tier": "plan", "ref": "P27.2", "rule": "cut_in_sentence", "severity": "block", "…": "…"}]},
  "shots":  {"pass": true,  "style_accept": {"reason": "night film, darker on purpose", "at": "…"}, "…": "…"},
  "render": {"pass": true,  "skipped_checks": null, "stopped": null, "reused_chunks": 0, "…": "…"},
  "final":  {"pass": true,  "…": "…"}
}}
```

## `CHECKS.md`
Thêm mục "Tiers": một bảng 5 hàng (tầng, đạt hay không, số lỗi, số cảnh báo, ngoại lệ, thời điểm). Dưới bảng là danh sách lỗi còn mở và danh sách ngoại lệ kèm lý do. Lệch phong cách đã chấp nhận hiện kèm lý do.

## Cổng render
Cổng đạt khi cả ba điều đúng:
- `tiers.plan.pass` đúng, và `fingerprint` của nó bằng dấu vân tay nguồn hiện tại;
- `tiers.shots`: mọi lỗi `block` đã sửa hoặc có ngoại lệ, và cùng dấu vân tay;
- không còn lỗi `warn` nào của tầng `shots`, hoặc `style_accept.reason` không rỗng.
